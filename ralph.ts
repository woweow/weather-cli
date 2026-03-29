import { $ } from "bun";
const STOP_TOKEN = "<ALL_TASKS_COMPLETED>";
const BLOCKED_TOKEN = "<FULLY_BLOCKED>";
const DEFAULT_MAX_ITERATIONS = 100;
const DEFAULT_MODEL = "sonnet";
const DEFAULT_CLI = "claude";
const DEFAULT_RESUME_FIRST = false;

const makePrompt = () => `
# Objective
Read the PRD and \`status-notes.md\`, choose something to work on, and complete it.
Re-orient every time by reading both before taking action.

Do not write tests for the sake of tests. If the project is completed, it is completed. (prevent running away with creating 100s of tests for the sake of them)

# Execution
1. Pick a next action item from the PRD and work on it. Action items are not defined in the PRD. It's up to you to evaluate the PRD and status notes in order to identify the next highest priority task. Tasks should be straightforward digestible chunks like a single feature or validation task or deployment action etc.
2. After completing a task, commit it.
3. Write a status note with format

- Current time (PST):
- What I did:
- How I verified it
- Notes:
- Blockers:

4. Stop
When you have completed a single task, stop and describe what you did and yield control back to the human. 

Special stop situations:
- If everything is completed (full PRD has been implemented and validated), return ${STOP_TOKEN} when you yield control back
- If you are blocked and can see that the previous task(s) were blocked on the same issue, return ${BLOCKED_TOKEN} when you yield control back to the human.

`;

const parseMaxIterations = (value: string | undefined) => {
	if (value === undefined) {
		return DEFAULT_MAX_ITERATIONS;
	}

	const parsed = Number.parseInt(value, 10);
	if (Number.isFinite(parsed) && parsed > 0) {
		return parsed;
	}

	return DEFAULT_MAX_ITERATIONS;
};

type CliTool = "claude" | "codex";

type RunOptions = {
	maxIterations: number;
	model: string;
	cli: CliTool;
	resumeFirst: boolean;
};

const parseBooleanFlag = (value: string | undefined, fallback: boolean) => {
	if (value === undefined) {
		return fallback;
	}
	if (value === "true" || value === "1" || value === "yes") {
		return true;
	}
	if (value === "false" || value === "0" || value === "no") {
		return false;
	}
	return fallback;
};

const parseArgs = (argv: string[]) => {
	let model = DEFAULT_MODEL;
	let cli: CliTool = DEFAULT_CLI;
	let resumeFirst = DEFAULT_RESUME_FIRST;

	for (let i = 0; i < argv.length; i += 1) {
		const arg = argv[i];
		if (arg === "--model" && argv[i + 1]) {
			model = argv[i + 1];
			i += 1;
			continue;
		}
		if (arg === "--cli" && argv[i + 1]) {
			const value = argv[i + 1];
			if (value === "claude" || value === "codex") {
				cli = value;
			}
			i += 1;
			continue;
		}
		if (arg === "--resume-first") {
			resumeFirst = true;
		}
	}

	resumeFirst = parseBooleanFlag(process.env.RALPH_RESUME_FIRST, resumeFirst);
	model = process.env.RALPH_MODEL ?? model;
	const envCli = process.env.RALPH_CLI;
	if (envCli === "claude" || envCli === "codex") {
		cli = envCli;
	}

	return { model, cli, resumeFirst };
};

const buildCommand = (cli: CliTool, model: string, prompt: string, shouldResume: boolean) => {
	if (cli === "claude") {
		if (shouldResume) {
			return $`claude -p --dangerously-skip-permissions --model ${model} --continue ${prompt}`;
		}
		return $`claude -p --dangerously-skip-permissions --model ${model} ${prompt}`;
	}

	if (shouldResume) {
		return $`codex exec resume --last --dangerously-bypass-approvals-and-sandbox --model ${model} ${prompt}`;
	}
	return $`codex exec --dangerously-bypass-approvals-and-sandbox --model ${model} ${prompt}`;
};

async function run(options: RunOptions) {
	const prompt = makePrompt();
	let output = "";
	let iteration = 1;
	while (!output.includes(STOP_TOKEN) && iteration <= options.maxIterations) {
		const isContinuation = iteration !== 1;
		const shouldResume = iteration === 1 ? options.resumeFirst : true;
		console.log(
			`[turn_start] iteration=${iteration} cli=${options.cli} model=${options.model} continuation=${isContinuation} resume=${shouldResume}`,
		);

		const command = buildCommand(options.cli, options.model, prompt, shouldResume);

		output = await command.text();
		console.log(
			`[turn_response] iteration=${iteration} chars=${output.length} stop=${output.includes(
				STOP_TOKEN,
			)} blocked=${output.includes(BLOCKED_TOKEN)}`,
		);
		console.log(`--- model output (turn ${iteration}) ---\n${output}\n--- end ---`);
		iteration += 1;
	}

	if (!output.includes(STOP_TOKEN)) {
		throw new Error(
			`Stopped after ${options.maxIterations} iterations without receiving ${STOP_TOKEN}.`,
		);
	}
	console.log(`[run_complete] iterations=${iteration - 1}`);
}

const maxIterations = parseMaxIterations(process.env.RALPH_MAX_ITERATIONS);
const { model, cli, resumeFirst } = parseArgs(process.argv.slice(2));

await run({ maxIterations, model, cli, resumeFirst });
