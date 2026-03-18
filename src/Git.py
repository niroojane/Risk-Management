import requests
from io import BytesIO
import base64

token = ''
repo_owner = ''
repo_name = ''
branch = ''
binance_api_key=''
binance_api_secret=''

class GitHub:

    def __init__(self,token,repo_owner,repo_name,branch):

        self.token=token
        self.repo_owner=repo_owner
        self.repo_name=repo_name
        self.branch=branch

    def push_or_update_file(self,df,file_name):
        # Prepare file path
        file_path = f'{file_name}.xlsx'
        
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=True,engine='openpyxl')
        excel_data = excel_buffer.getvalue()
        
        # Encode content to Base64
        encoded_content = base64.b64encode(excel_data).decode()
        
        # GitHub API URLs
        url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}'
        
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # --- STEP 1: Check if file exists to get SHA ---
        sha = None
        get_response = requests.get(url, headers=headers, params={'ref': self.branch})
        
        if get_response.status_code == 200:
            sha = get_response.json()['sha']
            print(f'🔁 File exists. Will update (SHA: {sha})')
        elif get_response.status_code == 404:
            print('🆕 File does not exist. Will create new.')
        else:
            print(f'❌ Error checking file existence: {get_response.status_code}')
            print(get_response.json())
            return
        
        # --- STEP 2: Prepare data payload ---
        data = {
            'message': f'Add/Update {file_name}.xlsx via API',
            'content': encoded_content,
            'branch': self.branch
        }
        if sha:
            data['sha'] = sha  # Needed for updates
        
        # --- STEP 3: PUT request to create/update file ---
        put_response = requests.put(url, headers=headers, json=data)
        
        if put_response.status_code in [200, 201]:
            print('✅ File pushed/updated successfully!')
        else:
            print(f'❌ Failed to push/update file: {put_response.status_code}')
            print(put_response.json())


    def create_or_replace_notebook(self,file_path, commit_message="Create/Replace Jupyter Notebook"):
        """
        Create or replace a Jupyter Notebook file in a GitHub repository.
        
        :param file_path: Path to the local Jupyter notebook file (.ipynb)
        :param repo_owner: GitHub username (repository owner)
        :param repo_name: Name of the repository
        :param token: GitHub personal access token with repo permissions
        :param commit_message: Commit message for creating/replacing the file
        :param branch: The branch where the file will be pushed (default is 'main')
        """
        # Read the file content and encode it in base64
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        encoded_content = base64.b64encode(file_content).decode("utf-8")
        
        # Define the API URL to upload or replace the file
        file_name = file_path.split("/")[-1]  # Get the file name
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{file_name}"
    
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
        # Data payload for creating or updating the file
        data = {
            "message": commit_message,
            "content": encoded_content,
            "branch": self.branch
        }
    
        # --- STEP 1: Check if the file exists to get the SHA ---
        get_response = requests.get(url, headers=headers)
        
        if get_response.status_code == 200:
            # If file exists, we need to get the SHA to replace it
            sha = get_response.json()['sha']
            data['sha'] = sha  # Include SHA for updating the file
            print(f"File '{file_name}' exists. Replacing the file...")
    
        elif get_response.status_code == 404:
            # If file does not exist, we will create it
            print(f"File '{file_name}' does not exist. Creating new file...")
        
        else:
            # If there’s an error in checking file existence
            print(f"❌ Error checking file existence: {get_response.status_code}")
            print(get_response.json())
            return
    
        # --- STEP 2: Make the PUT request to create or update the file ---
        response = requests.put(url, headers=headers, json=data)
    
        if response.status_code == 201 or response.status_code == 200:
            print(f"✅ File '{file_name}' successfully pushed/updated to GitHub!")
        else:
            print(f"❌ Failed to push/update file: {response.status_code}")
            print(response.json())