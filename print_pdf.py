import json
import argparse
import smtplib
import ssl
import email
import email.mime.multipart
import pathlib


def main():
    parser = argparse.ArgumentParser(
        description="Send a PDF to the email of an HP ePrint printer"
    )
    parser.add_argument("input_path", help="Path to the input PDF")
    args = parser.parse_args()

    pdf_path = pathlib.Path(args.input_path)

    secrets = json.load(
        open(
            pathlib.Path(__file__).parent.absolute() / "secrets.json",
            "r",
            encoding="utf-8",
        )
    )

    printer_email = secrets["printer_email"]

    sender_email = secrets["sender_email"]
    sender_password = secrets["sender_password"]
    sender_smtp_server = secrets["sender_smtp_server"]
    sender_smtp_port = secrets["sender_smtp_port"]

    # Create a multipart message and set headers
    message = email.mime.multipart.MIMEMultipart()
    message["From"] = sender_email
    message["To"] = printer_email
    message["Subject"] = "Print"

    # Open PDF file in binary mode
    with open(pdf_path, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = email.mime.base.MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email
    email.encoders.encode_base64(part)

    # Add header as key/value pair to attachment part
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {pdf_path.name}",
    )

    # Add attachment to message
    message.attach(part)

    # Send the email with SMTP TLS
    with smtplib.SMTP(sender_smtp_server, sender_smtp_port) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, printer_email, message.as_string())


if __name__ == "__main__":
    main()
