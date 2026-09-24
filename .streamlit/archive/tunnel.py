from pyngrok import ngrok
# Connect to your running Streamlit server (default port 8501)
public_url = ngrok.connect(8501)
print("Public URL:", public_url)
input("Press Enter to close tunnel...")