# IMPORTANT: This Streamlit script is intended to be run in a standard Python environment.
# It will not work properly in Pyodide or browser-based Python environments like JupyterLite.
# If you encounter `ModuleNotFoundError: No module named 'micropip'`, please run this using:
#     streamlit run mental_plan_processor.py

import streamlit as st
import pandas as pd
import requests
import openai

st.set_page_config(page_title="Mental Health Plan Generator", layout="wide")

# Provide your OpenAI API key (you can load this from secrets or environment for safety)
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.warning("🔑 OpenAI API key missing in secrets. Chatbot won't work.")

# Session state for login
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Login UI
if not st.session_state.authenticated:
    st.title("🔐 Sign In")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        if username == "admin" and password == "1234":
            st.session_state.authenticated = True
            st.success("✅ Login successful! Use the menu to proceed.")
        else:
            st.error("❌ Invalid credentials. Try again.")

if st.session_state.authenticated:
    st.title("🧠 AI-Powered Patient Treatment Generator")

    # Chatbot Section with GPT support
    st.subheader("🤖 Ask the AI Assistant")
    user_input = st.text_input("You:", key="chat_input")

    if user_input:
        st.session_state.chat_history.append(("You", user_input))

        try:
            gpt_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "You are a helpful medical AI assistant."}] +
                         [{"role": "user", "content": m[1]} if m[0] == "You" else {"role": "assistant", "content": m[1]}
                          for m in st.session_state.chat_history if m[0] != "AI" or m[1] != "Loading..."]
            )
            reply = gpt_response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            reply = f"❌ OpenAI error: {str(e)}"

        st.session_state.chat_history.append(("AI", reply))

    for speaker, message in st.session_state.chat_history:
        with st.chat_message(speaker):
            st.markdown(message)

    def analyze_and_generate_plan(row):
        prompt = f"""
You are a medical AI assistant. Analyze the following patient details and generate:
- Condition Risk Level
- Initial Treatment Plan
- Adapted Plan based on feedback
- Final Affordable Plan (considering income level and location)

Patient Info:
{row.to_dict()}
"""
        try:
            response = requests.post(
                "https://n8n.yourdomain.com/webhook/ai-patient-plan",
                json={"text": prompt},
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    uploaded_file = st.file_uploader("📤 Upload any patient data file (CSV, Excel)", type=["csv", "xls", "xlsx"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                data = pd.read_csv(uploaded_file)
            else:
                data = pd.read_excel(uploaded_file)

            st.success("✅ File uploaded successfully!")
            st.write("### 📊 Preview of Uploaded Data")
            st.dataframe(data.head())

            st.write("### 🤖 AI-Generated Treatment Suggestions")
            results = []

            for _, row in data.iterrows():
                output = analyze_and_generate_plan(row)
                if "error" in output:
                    st.warning(f"❌ Error processing row: {output['error']}")
                    continue

                results.append({
                    "Patient ID": row.get("id", "N/A"),
                    "Condition": row.get("condition", "N/A"),
                    "Risk Level": output.get("risk", "N/A"),
                    "Initial Plan": output.get("initial_plan", "N/A"),
                    "Adapted Plan": output.get("adapted_plan", "N/A"),
                    "Final Plan": output.get("final_plan", "N/A")
                })

            if results:
                df = pd.DataFrame(results)
                st.dataframe(df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download AI Plans as CSV", data=csv, file_name="ai_treatment_plans.csv", mime='text/csv')
            else:
                st.info("No valid results generated.")

        except Exception as e:
            st.error(f"❌ Failed to read file: {e}")
    else:
        st.info("Please upload a patient data file to begin.")
