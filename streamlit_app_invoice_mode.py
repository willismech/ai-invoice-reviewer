
import streamlit as st
import openai
import os
import json
import requests
from requests.auth import HTTPBasicAuth

# Load credentials from Streamlit secrets
SERVICETRADE_USERNAME = st.secrets.get("SERVICETRADE_USERNAME")
SERVICETRADE_PASSWORD = st.secrets.get("SERVICETRADE_PASSWORD")
SERVICETRADE_API_BASE = "https://app.servicetrade.com/api"

openai.api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

# Streamlit setup
st.set_page_config(page_title="Invoice QA Review", layout="wide")
st.title("🧾 Invoice QA Assistant for ServiceTrade")

invoice_id = st.text_input("Enter ServiceTrade Invoice ID:")

if st.button("🔍 Analyze Invoice"):
    if not invoice_id.strip():
        st.warning("Please enter a valid invoice ID.")
    else:
        with st.spinner("Fetching invoice and job data from ServiceTrade..."):
            job_data = None
            try:
                # Step 1: Get invoice
                invoice_response = requests.get(
                    f"{SERVICETRADE_API_BASE}/invoice/{invoice_id}",
                    auth=HTTPBasicAuth(SERVICETRADE_USERNAME, SERVICETRADE_PASSWORD)
                )

                if invoice_response.status_code != 200:
                    st.error(f"Could not fetch invoice with ID {invoice_id}. Status code: {invoice_response.status_code}")
                else:
                    invoice_data = invoice_response.json()
                    job_id = invoice_data.get("job", {}).get("id")

                    if not job_id:
                        st.error("Job ID not found in invoice response.")
                    else:
                        # Step 2: Get job details
                        job_response = requests.get(
                            f"{SERVICETRADE_API_BASE}/job/{job_id}",
                            auth=HTTPBasicAuth(SERVICETRADE_USERNAME, SERVICETRADE_PASSWORD)
                        )

                        if job_response.status_code == 200:
                            job_data = job_response.json()
                        else:
                            st.error(f"Could not fetch job with ID {job_id}. Status code: {job_response.status_code}")

            except Exception as e:
                st.error(f"Error contacting ServiceTrade API: {e}")

        if job_data:
            with st.spinner("Analyzing invoice with AI..."):
                job_text = json.dumps(job_data, indent=2)
                prompt = f"""You are an expert HVAC invoice reviewer. Review this job data against the following criteria:

INVOICE REVIEW POLICY:
- The phrase "Job complete" is the final text in the invoice.
- Labor rates are accurate per customer:
    - Piedmont Urgent Care: $110/hr
    - US Fitness: $125/hr
    - PM Clients: $115/hr (regular), $172.50/hr (OT)
    - Non-PM Clients: $155/hr (regular), $232.50/hr (OT)
- Number of labor hours is accurate.
- A signed work acknowledgment is attached and clearly visible to the customer.
    - Only one acknowledgment should be present.
- Spelling and grammar must be correct.
- A 2-hour minimum labor charge applies to all T&M jobs.
- If work continues into the next hour, a full extra hour is billed.
- Pictures of supply house receipts should be attached.
- Tech comments are visible and listed in chronological order (newest last).
- If it's a sewer clog or cleanout:
    - There must be MISC material for large sewer machine or jet
    - 2 people must be present for big jet

Review this job data:
""" + job_text + """ 

Return your results in JSON like this:
{
  "corrected": "Cleaned-up invoice text...",
  "alerts": ["Missing signature attachment", "Labor rate does not match client"],
  "suggestions": "Consider rephrasing the summary to include serial number."
}
"""

                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2
                    )
                    reply = response.choices[0].message['content']

                    try:
                        result = json.loads(reply)
                        st.success("✅ Analysis Complete")

                        st.subheader("Corrected Invoice Text")
                        st.text_area("", result.get("corrected", ""), height=200)

                        st.subheader("Alerts")
                        for alert in result.get("alerts", []):
                            st.warning(alert)

                        st.subheader("Suggestions")
                        st.info(result.get("suggestions", "None"))

                    except Exception as e:
                        st.error("❌ Error parsing AI response. Here's the raw output:")
                        st.code(reply)
                except Exception as e:
                    st.error(f"OpenAI API error: {e}")

st.markdown("---")
st.caption("Built for Willis Mechanical | ServiceTrade QA Tool")
