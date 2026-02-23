import os
import time
from utils.logger import logger

class WhatsAppAPIClient:
    """
    Wrapper for whatsapp-python library to interact with WhatsApp Cloud API.
    Requires Meta Developer Account and Business API setup.
    """
    def __init__(self):
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.messenger = None
        
        if self.access_token and self.phone_number_id:
            try:
                # Import here to avoid dependency if not installed/needed
                from whatsapp import WhatsApp
                self.messenger = WhatsApp(self.access_token, phone_number_id=self.phone_number_id)
                logger.info("WhatsApp Cloud API initialized successfully.")
            except ImportError:
                logger.error("whatsapp-python library not installed. Please install it to use Cloud API.")
            except Exception as e:
                logger.error(f"Failed to initialize WhatsApp Cloud API: {e}")
        else:
            logger.warning("WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID not set. Cloud API disabled.")

    def is_available(self):
        return self.messenger is not None

    def send_message(self, target, message):
        """
        Sends a message using the Cloud API.
        Target must be a phone number in international format (e.g., '15551234567').
        Note: The API requires phone numbers, not contact names.
        """
        if not self.is_available():
            logger.error("WhatsApp Cloud API not configured.")
            return False

        try:
            # Clean target number (remove +, spaces, dashes)
            clean_target = "".join(filter(str.isdigit, str(target)))
            
            logger.info(f"Sending Cloud API message to {clean_target}")
            
            # Send text message
            response = self.messenger.send_message(
                message=message,
                recipient_id=clean_target
            )
            
            # Check response status
            # The library usually returns a dict with 'id' or raises an error
            if response and 'messages' in response:
                 logger.info(f"Message sent successfully via Cloud API. ID: {response['messages'][0]['id']}")
                 return True
            else:
                 logger.error(f"Failed to send message via Cloud API. Response: {response}")
                 return False
                 
        except Exception as e:
            logger.error(f"Error sending WhatsApp Cloud API message: {e}")
            return False

if __name__ == "__main__":
    # Test
    client = WhatsAppAPIClient()
    if client.is_available():
        client.send_message("15550000000", "Hello from Ceaser AI!")
