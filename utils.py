import smtplib
import streamlit as st
from email.message import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def send_maintenance_alert(selected_plates):
    """Sends an email alert when vehicles are queued for maintenance."""
    try:
        # Check if the input is a list, and join it into a readable string
        if isinstance(selected_plates, list):
            plates_str = ", ".join(selected_plates)
            vehicle_count = len(selected_plates)
        else:
            plates_str = str(selected_plates)
            vehicle_count = 1

        msg = EmailMessage()
        msg['Subject'] = f"🚨 FLEET WORKSHOP ALERT: {vehicle_count} Vehicle(s) Queued"
        msg['From'] = st.secrets["EMAIL_USER"]
        msg['To'] = "tommydeso88@gmail.com" 
        msg.set_content(
            f"Fleet Intelligence System Update:\n\n"
            f"The following vehicles have been officially flagged and routed to the maintenance workshop:\n\n"
            f"Vehicle Plates: {plates_str}\n\n"
            f"Action Required: Please prepare the workshop for these incoming assets."
        )

        # Using Gmail SMTP - Ensure you use an App Password in your secrets.toml
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            smtp.send_message(msg)
            
        return True
    except Exception as e:
        # Printing to the terminal console guarantees we see the error even if Streamlit reruns
        print(f"CRITICAL EMAIL ERROR: {e}") 
        st.error(f"Email failed to send: {e}")
        return False

def generate_fleet_report(df, filename="fleet_report.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "NGO Fleet Maintenance Report")
    c.line(50, height - 60, width - 50, height - 60)
    
    y = height - 100
    c.setFont("Helvetica", 12)
    
    for _, row in df.iterrows():
        # Ensure this line is indented with 8 spaces
        c.drawString(50, y, f"Plate: {row['plate_number']} | Risk: {row['breakdown_risk_score']}% | Status: {row['risk_status']}")
        # Ensure this line is also indented with 8 spaces
        y -= 25 
            
    c.save()
    return filename