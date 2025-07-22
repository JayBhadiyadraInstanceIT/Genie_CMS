import requests
import json
import time
import uuid

class DatabaseAgentClient:
    def __init__(self, base_url="http://localhost:10002"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_agent_info(self):
        """Get agent information and capabilities."""
        try:
            response = self.session.get(f"{self.base_url}/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting agent info: {e}")
            return None
    
    def send_message(self, message, context_id=None):
        """Send a message to the agent."""
        if not context_id:
            context_id = str(uuid.uuid4())
        
        payload = {
            "message": {
                "parts": [
                    {"root": {"text": message}}
                ]
            },
            "context_id": context_id
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/execute",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json(), context_id
        except Exception as e:
            print(f"Error sending message: {e}")
            return None, context_id
    
    def chat_loop(self):
        """Interactive chat loop."""
        print("Database Query Agent Chat")
        print("Type 'quit' to exit, 'info' for agent information")
        print("-" * 50)
        
        context_id = str(uuid.uuid4())
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'info':
                    info = self.get_agent_info()
                    if info:
                        print(f"\nAgent Info:")
                        print(json.dumps(info, indent=2))
                    continue
                
                if not user_input:
                    continue
                
                print("Processing...")
                response, context_id = self.send_message(user_input, context_id)
                
                if response:
                    print(f"\nAgent: {self.extract_response_text(response)}")
                else:
                    print("Failed to get response")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def extract_response_text(self, response):
        """Extract text from agent response."""
        try:
            # Handle different response formats
            if isinstance(response, dict):
                if 'artifacts' in response:
                    artifacts = response['artifacts']
                    if artifacts and len(artifacts) > 0:
                        parts = artifacts[0].get('parts', [])
                        if parts:
                            return parts[0].get('root', {}).get('text', 'No text response')
                
                if 'message' in response:
                    parts = response['message'].get('parts', [])
                    if parts:
                        return parts[0].get('root', {}).get('text', 'No text response')
            
            return str(response)
        except Exception:
            return str(response)


def main():
    """Main function to run the test client."""
    client = DatabaseAgentClient()
    
    # Test connection
    print("🔍 Testing connection to agent...")
    info = client.get_agent_info()
    
    if info:
        print("✅ Agent is running!")
        print(f"Agent Name: {info.get('name', 'Unknown')}")
        print(f"Version: {info.get('version', 'Unknown')}")
        
        # Start chat loop
        client.chat_loop()
    else:
        print("Could not connect to agent. Make sure it's running on http://localhost:10002")
        print("\nTo start the agent, run:")
        print("python -m cms_agent_adk")


if __name__ == "__main__":
    main()
