import requests
import os
import json

URL = 'https://api.llms.afterhoursdev.com/chat/completions'
API_KEY = os.environ.get("LLAMA_API_KEY")
SESSION_TOKEN

thread = []

# make the api call for completion
def callAPI(prompt):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}',
        'SESSION-TOKEN': SESSION_TOKEN or ''
    }

    body = {
        'model': "meta-llama3.3-70b",
        'messages': thread,
        'system': 'You are a chatbot meant to teach geography. Any answer to a question should be accompanied by a description of where in the world the relevant place is.',
        'temperature': 0.5,
        'maxGenLen': 512
    }
    
    response = requests.post(URL, headers=headers, json=body)

    if response.status_code != 200:
        raise Exception(f"Llama API error: {response.status_code} {response.text}")
  
    return response.json()


def main():
    while True:
        prompt = input("Enter a prompt: ")
        if (prompt == 'quit'):
            break
        try:
            thread.append({
                'role': 'user',
                'message': prompt
            })

            # get the response from the API, add to thread and leave
            response = callAPI(prompt)['generation'].strip()
            print(response)
            thread.append({
                'role': 'assistant',
                'message': response
            })
        except Exception as e:
            print(f"Error: {str(e)}")
            break


if __name__ == "__main__":
    main()