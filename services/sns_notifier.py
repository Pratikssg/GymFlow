import boto3
import os
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the SNS client
sns = boto3.client('sns', region_name='ap-south-1')

# Topic ARNs from environment variables or defaults
TOPICS = {
    'reservation': os.getenv('SNS_RESERVATION_TOPIC', 'arn:aws:sns:ap-south-1:549328952222:GymFlow_Reservation_Confirmation'),
    'equipment': os.getenv('SNS_EQUIPMENT_TOPIC', 'arn:aws:sns:ap-south-1:549328952222:GymFlow_Equipment_Alerts'),
    'reminder': os.getenv('SNS_REMINDER_TOPIC', 'arn:aws:sns:ap-south-1:549328952222:GymFlow_User_Notifications')
}

# Email validation pattern
EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w{2,4}$"


def notify(destination: str, message: str, subject: str = 'GymFlow Notification') -> bool:
    """
    Publish a message to an SNS topic or to a subscribed user email (via 'reminder' topic).

    Parameters:
        destination (str): A topic key (e.g. 'reservation') or an email address.
        message (str): Message content.
        subject (str): Optional email subject.

    Returns:
        bool: True if message sent, False otherwise.
    """
    try:
        # Check if destination is an email
        if re.match(EMAIL_REGEX, destination):
            # Send via 'reminder' topic
            topic_arn = TOPICS.get('reminder')
            if not topic_arn:
                logger.error("❌ Reminder topic ARN is not set.")
                return False

            response = sns.publish(
                TopicArn=topic_arn,
                Message=message,
                Subject=subject
            )
            logger.info(f"📧 Email message sent via 'reminder' topic (email must be subscribed) | ID: {response.get('MessageId')}")
            return True

        # Else treat as topic key
        topic_arn = TOPICS.get(destination)
        if not topic_arn:
            logger.error(f"❌ Invalid topic key: '{destination}'. Must be one of: {list(TOPICS.keys())}")
            return False

        response = sns.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject=subject
        )
        logger.info(f"✅ SNS message sent to topic '{destination}' | Message ID: {response.get('MessageId')}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to send SNS message: {e}")
        return False


def subscribe_user_email(email: str, topic_key: str = 'reminder') -> bool:
    """
    Subscribe a user's email to a specified SNS topic.

    Parameters:
        email (str): User's email address (must be valid).
        topic_key (str): SNS topic key.

    Returns:
        bool: True if subscription was initiated, False otherwise.
    """
    if not re.match(EMAIL_REGEX, email):
        logger.warning(f"⚠️ Invalid email format: {email}")
        return False

    topic_arn = TOPICS.get(topic_key)
    if not topic_arn:
        logger.error(f"❌ Invalid topic key: '{topic_key}'. Must be one of: {list(TOPICS.keys())}")
        return False

    try:
        sns.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=email
        )
        logger.info(f"📨 Subscription initiated: '{email}' -> topic '{topic_key}'. Confirm via email to activate.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to subscribe '{email}' to topic '{topic_key}': {e}")
        return False
