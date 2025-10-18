"""
Test script for RAG chatbot endpoint
"""

import requests
import json


BASE_URL = "http://localhost:8000"


def test_chat_endpoint():
    """Test the chat endpoint"""

    print("\n" + "="*70)
    print("Testing AURA RAG Chatbot Endpoint")
    print("="*70 + "\n")

    # Step 1: List available sessions
    print("Step 1: Getting available sessions...")
    response = requests.get(f"{BASE_URL}/chat/sessions")

    if response.status_code == 200:
        sessions_data = response.json()
        print(f"Found {sessions_data['count']} sessions")

        if sessions_data['sessions']:
            # Use the most recent session (last in list)
            session_id = sessions_data['sessions'][-1]['session_id']
            print(f"Using session: {session_id}\n")
        else:
            print("No sessions available. Please run test_agents.py first.")
            return
    else:
        print(f"Error getting sessions: {response.status_code}")
        return

    # Step 2: Send first chat message
    print("Step 2: Sending first message...")
    chat_request = {
        "message": "What are the main findings about machine learning in healthcare?",
        "session_id": session_id,
        "conversation_id": "test_conversation"
    }

    response = requests.post(
        f"{BASE_URL}/chat/",
        json=chat_request
    )

    if response.status_code == 200:
        chat_response = response.json()
        print(f"\nQuestion: {chat_request['message']}")
        print(f"\nResponse: {chat_response['response'][:500]}...\n")
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return

    # Step 3: Send follow-up message
    print("Step 3: Sending follow-up message...")
    follow_up_request = {
        "message": "Can you tell me more about the ethical considerations?",
        "session_id": session_id,
        "conversation_id": "test_conversation"
    }

    response = requests.post(
        f"{BASE_URL}/chat/",
        json=follow_up_request
    )

    if response.status_code == 200:
        chat_response = response.json()
        print(f"\nQuestion: {follow_up_request['message']}")
        print(f"\nResponse: {chat_response['response'][:500]}...\n")
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return

    # Step 4: Get conversation history
    print("Step 4: Getting conversation history...")
    response = requests.get(
        f"{BASE_URL}/chat/history/{session_id}/test_conversation"
    )

    if response.status_code == 200:
        history_data = response.json()
        print(f"\nConversation has {len(history_data['messages'])} messages")

        for i, msg in enumerate(history_data['messages']):
            print(f"\n{i+1}. {msg['role'].upper()}: {msg['content'][:100]}...")
    else:
        print(f"Error getting history: {response.status_code}")

    print("\n" + "="*70)
    print("Chatbot Test Complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        test_chat_endpoint()
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to server.")
        print("Please start the server first:")
        print("  cd aura_research && python main.py\n")
    except Exception as e:
        print(f"\nTest error: {str(e)}\n")
