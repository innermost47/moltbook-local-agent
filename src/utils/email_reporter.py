import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from src.settings import settings
from src.utils import log


class EmailReporter:
    def __init__(self):
        self.enabled = (
            settings.ENABLE_EMAIL_REPORTS and settings.SMTP_USER and settings.EMAIL_TO
        )

    def send_session_report(self, tracker_data: dict, ai_summary: any):
        if not self.enabled:
            log.info("📧 Email reports disabled, skipping.")
            return

        try:
            subject = f"🎵 Olivier Session Report | XP: {tracker_data['xp']} | {datetime.now().strftime('%H:%M')}"

            log_html = ""
            for entry in tracker_data["history"]:
                color = "#4CAF50" if entry["status"] == "✅" else "#f44336"
                log_html += f"""
                <tr>
                    <td>{entry['time']}</td>
                    <td style="color: {color};"><strong>{entry['status']}</strong></td>
                    <td>{entry['action']}</td>
                    <td>{entry['domain']}</td>
                    <td>{entry['xp_gain']} XP</td>
                </tr>
                """

            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6;">
                <div style="background: #2c3e50; color: white; padding: 25px; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0;">🎷 Olivier Harmonique</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.8;">Session Resonance Report</p>
                </div>

                <div style="padding: 20px; border: 1px solid #ddd; border-top: none;">
                    <div style="display: flex; gap: 20px; margin-bottom: 30px;">
                        <div style="flex: 1; background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border-bottom: 4px solid #4CAF50;">
                            <span style="font-size: 12px; text-transform: uppercase; color: #666;">Total XP</span><br>
                            <strong style="font-size: 24px; color: #2c3e50;">{tracker_data['xp']}</strong>
                        </div>
                        <div style="flex: 1; background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border-bottom: 4px solid #2196f3;">
                            <span style="font-size: 12px; text-transform: uppercase; color: #666;">Success Rate</span><br>
                            <strong style="font-size: 24px; color: #2c3e50;">{tracker_data['success_rate']:.1f}%</strong>
                        </div>
                    </div>

                    <div style="background: #fff3e0; padding: 20px; border-radius: 8px; margin-bottom: 30px; border-left: 5px solid #ff9800;">
                        <h3 style="margin-top: 0; color: #e65100;">🧠 Internal Reflection</h3>
                        <p><strong>Objective:</strong> {ai_summary.session_title}</p>
                        <p><strong>What I learned:</strong><br>{ai_summary.key_learnings}</p>
                        <p style="color: #2c3e50; font-style: italic;">" {ai_summary.mental_state_evolution} "</p>
                    </div>

                    <h3>📜 Session Logs</h3>
                    <table width="100%" style="border-collapse: collapse; font-size: 14px;">
                        <thead>
                            <tr style="background: #eee; text-align: left;">
                                <th style="padding: 10px;">Time</th>
                                <th style="padding: 10px;">Status</th>
                                <th style="padding: 10px;">Action</th>
                                <th style="padding: 10px;">Mode</th>
                                <th style="padding: 10px;">XP</th>
                            </tr>
                        </thead>
                        <tbody>
                            {log_html}
                        </tbody>
                    </table>
                </div>

                <div style="text-align: center; font-size: 12px; color: #999; margin-top: 20px;">
                    Next Session Priority: <strong>{ai_summary.next_session_priority}</strong>
                </div>
            </body>
            </html>
            """

            self._send_email(subject, html_content)

        except Exception as e:
            log.error(f"❌ Failed to send session report: {e}")

    def _send_email(self, subject: str, html_body: str):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.EMAIL_TO
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        log.success(f"📧 Report sent to {settings.EMAIL_TO}")
