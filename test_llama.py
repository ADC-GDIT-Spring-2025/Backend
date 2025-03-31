import requests
import os
import json

url = 'https://api.llms.afterhoursdev.com/chat/completions'
api_key = os.environ.get("LLAMA_API_KEY")

thread = []

# make the api call for completion
def callAPI(prompt):
  response = requests.post(url, headers={
      'Content-Type': 'application/json',
      'Authorization': f'Bearer {api_key}',
      'SESSION-TOKEN': 'session1'
  }, json={
        'model': "meta-llama3.3-70b",
        'messages': thread,
        'system': 'You are a chatbot meant to teach geography. Any answer to a question should be accompanied by a description of where in the world the relevant place is.',
        'temperature': 0.5,
        'maxGenLen': 512
  })

  if response.status_code != 200:
      raise Exception(f"Llama API error: {response.status_code} {response.text}")
  
  return response.json()

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