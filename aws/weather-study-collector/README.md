# weather-study-collector Lambda

Local deployment wrapper for the weather study collector Lambda.

Examples:

```bash
python3 aws/weather-study-collector/deploy.py \
  --bucket weather-study-raw-084375548651-us-west-2 \
  --prefix raw-lambda-smoke

aws lambda invoke \
  --function-name weather-study-collector-dev \
  --profile dev \
  --region us-west-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"places":["Seattle,WA"]}' \
  /tmp/weather-study-lambda-response.json
```

Notes:

- The deploy script packages the in-repo collector, study, weather, and Kalshi source packages into one Lambda zip.
- It creates or updates a minimal IAM role for Lambda basic logs plus S3 writes to the configured bucket/prefix.
- The Lambda writes the same raw capture contract already validated by `weather-study-cli`.
