import json
from crawler import process_job
from job_manager import save_job, get_job, update_job_status

def lambda_handler(event, context):
    if event['httpMethod'] == 'POST':
        job_data = json.loads(event['body'])
        job_id = save_job(job_data)
        response = {
            "statusCode": 200,
            "body": json.dumps({"job_id": job_id})
        }
        return response

    if event['httpMethod'] == 'GET':
        job_id = event['queryStringParameters']['job_id']
        job_data = get_job(job_id)
        response = {
            "statusCode": 200,
            "body": json.dumps(job_data)
        }
        return response

    if event['httpMethod'] == 'PUT':
        job_id = event['queryStringParameters']['job_id']
        job_data = json.loads(event['body'])
        update_job_status(job_id, job_data)
        response = {
            "statusCode": 200,
            "body": json.dumps({"message": "Job status updated."})
        }
        return response
