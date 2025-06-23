import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')

# Table References
db = {
    'Users': dynamodb.Table('Users'),
    'Equipment': dynamodb.Table('Equipment'),
    'Reservations': dynamodb.Table('Reservations'),
    'Workouts': dynamodb.Table('Workouts')
}

# ---------------------- USERS TABLE ----------------------

def get_user_by_email(email):
    try:
        response = db['Users'].get_item(Key={'email': email})
        return response.get('Item', None)
    except ClientError as e:
        print("❌ Error getting user:", e)
        return None

def add_user(user_data):
    try:
        db['Users'].put_item(Item=user_data)
        return True
    except ClientError as e:
        print("❌ Error adding user:", e)
        return False

# ---------------------- EQUIPMENT TABLE ----------------------

def get_all_equipment():
    try:
        response = db['Equipment'].scan()
        return response.get('Items', [])
    except ClientError as e:
        print("❌ Error fetching equipment:", e)
        return []

def update_equipment_status(equipment_id, status):
    try:
        db['Equipment'].update_item(
            Key={'equipment_id': equipment_id},
            UpdateExpression='SET availability = :val',
            ExpressionAttributeValues={':val': status}
        )
        return True
    except ClientError as e:
        print("❌ Error updating equipment status:", e)
        return False

# ---------------------- RESERVATIONS TABLE ----------------------

def create_reservation(reservation_data):
    try:
        db['Reservations'].put_item(Item=reservation_data)
        return True
    except ClientError as e:
        print("❌ Error creating reservation:", e)
        return False

def get_reservations_by_user(user_id):
    try:
        response = db['Reservations'].query(
            IndexName='user_id-index',  # Make sure this GSI exists
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        return response.get('Items', [])
    except ClientError as e:
        print("❌ Error getting reservations:", e)
        return []

# ---------------------- WORKOUTS TABLE ----------------------

def log_workout(workout_data):
    try:
        db['Workouts'].put_item(Item=workout_data)
        return True
    except ClientError as e:
        print("❌ Error logging workout:", e)
        return False

def get_user_workouts(user_id):
    try:
        response = db['Workouts'].query(
            IndexName='user_id-index',  # Ensure GSI exists
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        return response.get('Items', [])
    except ClientError as e:
        print("❌ Error fetching workouts:", e)
        return []
