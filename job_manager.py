import boto3
import uuid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('WebScrapingJobs')

def save_job(job_data):
    job_id = str(uuid.uuid4())
    job_data['job_id'] = job_id
    table.put_item(Item=job_data)
    return job_id

def get_job(job_id):
    response = table.get_item(Key={'job_id': job_id})
    return response.get('Item')

def update_job_status(job_id, status):
    table.update_item(
        Key={'job_id': job_id},
        UpdateExpression="set job_status = :s",
        ExpressionAttributeValues={':s': status},
        ReturnValues="UPDATED_NEW"
    )
