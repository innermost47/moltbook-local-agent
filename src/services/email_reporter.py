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

    def send_session_report(
        self,
        agent_name: str,
        karma: int,
        actions: list,
        learnings: str,
        next_plan: str,
        content_urls: list,
        session_metrics: dict = None,
        supervisor_verdict: dict = None,
        global_progression: dict = None,
    ):

        if not self.enabled:
            log.info("Email reports disabled, skipping")
            return

        try:
            successes = [
                a
                for a in actions
                if not a.startswith("FAILED") and not a.startswith("SKIPPED")
            ]
            failures = [
                a for a in actions if a.startswith("FAILED") or a.startswith("SKIPPED")
            ]

            subject = f"🤖 Moltbook Agent Report - {agent_name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background: #4CAF50; color: white; padding: 20px; border-radius: 5px; }}
                    .stats {{ background: #f4f4f4; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                    .metrics {{ background: #e8f5e9; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }}
                    .progression {{ background: #fff3e0; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #ff9800; }}
                    .supervisor {{ background: #e3f2fd; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #2196f3; }}
                    .grade {{ font-size: 48px; font-weight: bold; text-align: center; padding: 10px; }}
                    .grade-A {{ color: #4CAF50; }}
                    .grade-B {{ color: #8BC34A; }}
                    .grade-C {{ color: #FFC107; }}
                    .grade-D {{ color: #FF9800; }}
                    .grade-F {{ color: #f44336; }}
                    .section {{ margin: 20px 0; }}
                    .success {{ color: #4CAF50; }}
                    .failure {{ color: #f44336; }}
                    .url-list {{ list-style: none; padding: 0; }}
                    .url-item {{ background: #e3f2fd; padding: 10px; margin: 5px 0; border-radius: 3px; }}
                    .url-item a {{ color: #1976d2; text-decoration: none; }}
                    .url-item a:hover {{ text-decoration: underline; }}
                    .learnings {{ background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; border-radius: 3px; }}
                    .plan {{ background: #d1ecf1; padding: 15px; border-left: 4px solid #17a2b8; border-radius: 3px; }}
                    .metric-row {{ display: flex; justify-content: space-between; margin: 10px 0; }}
                    .metric-label {{ font-weight: bold; }}
                    .trend-up {{ color: #4CAF50; }}
                    .trend-down {{ color: #f44336; }}
                    .trend-stable {{ color: #ff9800; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🤖 Moltbook Agent Session Report</h1>
                    <p><strong>Agent:</strong> {agent_name}</p>
                    <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            """

            if session_metrics and global_progression:
                rejection_rate = (
                    (
                        session_metrics["supervisor_rejections"]
                        / session_metrics["total_actions"]
                        * 100
                    )
                    if session_metrics["total_actions"] > 0
                    else 0
                )
                failure_rate = (
                    (
                        session_metrics["execution_failures"]
                        / session_metrics["total_actions"]
                        * 100
                    )
                    if session_metrics["total_actions"] > 0
                    else 0
                )

                trend_class = (
                    "trend-up"
                    if global_progression["trend"] == "📈 IMPROVING"
                    else (
                        "trend-down"
                        if global_progression["trend"] == "📉 DECLINING"
                        else "trend-stable"
                    )
                )

                html_content += f"""
                <div class="metrics">
                    <h2>📊 Session Performance Metrics</h2>
                    <div class="metric-row">
                        <span class="metric-label">Session Score:</span>
                        <span><strong>{session_metrics['session_score']:.1f}%</strong></span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Total Actions:</span>
                        <span>{session_metrics['total_actions']}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Supervisor Rejections:</span>
                        <span>{session_metrics['supervisor_rejections']} ({rejection_rate:.1f}%)</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Execution Failures:</span>
                        <span>{session_metrics['execution_failures']} ({failure_rate:.1f}%)</span>
                    </div>
                </div>

                <div class="progression">
                    <h2>📈 Global Progression</h2>
                    <div class="metric-row">
                        <span class="metric-label">Alignment Score:</span>
                        <span><strong>{global_progression['global_score']:.1f}/100</strong></span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Trend:</span>
                        <span class="{trend_class}"><strong>{global_progression['trend']}</strong></span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Change:</span>
                        <span class="{trend_class}"><strong>{global_progression['progression_rate']:+.1f}%</strong></span>
                    </div>
                </div>
                """

            if supervisor_verdict:
                grade = supervisor_verdict.get("grade", "C")
                grade_class = f"grade-{grade[0]}"

                html_content += f"""
                <div class="supervisor">
                    <h2>🧐 Supervisor Final Verdict</h2>
                    <div class="grade {grade_class}">
                        Grade: {grade}
                    </div>
                    <p><strong>Overall Assessment:</strong></p>
                    <p>{supervisor_verdict.get('overall_assessment', 'N/A')}</p>
                    <p><strong>Main Weakness:</strong></p>
                    <p style="color: #f44336;">{supervisor_verdict.get('main_weakness', 'N/A')}</p>
                    <p><strong>Directive for Next Session:</strong></p>
                    <p style="color: #2196f3; font-weight: bold;">{supervisor_verdict.get('directive_next_session', 'N/A')}</p>
                </div>
                """

            html_content += f"""
                <div class="stats">
                    <h2>📊 Session Statistics</h2>
                    <p><strong>Karma:</strong> {karma}</p>
                    <p><strong>Total Actions:</strong> {len(actions)}</p>
                    <p class="success"><strong>✅ Successful:</strong> {len(successes)}</p>
                    <p class="failure"><strong>❌ Failed/Skipped:</strong> {len(failures)}</p>
                </div>
                
                <div class="section">
                    <h2>✅ Successful Actions</h2>
                    <ul>
            """

            for action in successes:
                html_content += f"<li class='success'>{action}</li>"

            html_content += """
                    </ul>
                </div>
            """

            if failures:
                html_content += """
                <div class="section">
                    <h2>❌ Failed/Skipped Actions</h2>
                    <ul>
                """
                for action in failures:
                    html_content += f"<li class='failure'>{action}</li>"

                html_content += """
                    </ul>
                </div>
                """

            if content_urls:
                html_content += """
                <div class="section">
                    <h2>🔗 Created Content</h2>
                    <ul class="url-list">
                """
                for item in content_urls:
                    if isinstance(item, str):
                        html_content += f"""
                        <li class="url-item">
                            <strong>🔗 Content:</strong><br>
                            <a href="{item}" target="_blank">{item}</a>
                        </li>
                        """
                        continue
                    if item["type"] == "post":
                        html_content += f"""
                        <li class="url-item">
                            <strong>📄 Post:</strong> {item['title']}<br>
                            <a href="{item['url']}" target="_blank">{item['url']}</a>
                        </li>
                        """
                    elif item["type"] == "comment":
                        html_content += f"""
                        <li class="url-item">
                            <strong>💬 Comment</strong> on post {item['post_id']}<br>
                            <a href="{item['url']}" target="_blank">{item['url']}</a>
                        </li>
                        """
                    elif item["type"] == "reply":
                        html_content += f"""
                        <li class="url-item">
                            <strong>↩️ Reply</strong> to comment {item['parent_comment_id']}<br>
                            <a href="{item['url']}" target="_blank">{item['url']}</a>
                        </li>
                        """

                html_content += """
                    </ul>
                </div>
                """

            html_content += f"""
                <div class="section">
                    <h2>🧠 Learnings</h2>
                    <div class="learnings">
                        {learnings}
                    </div>
                </div>
                
                <div class="section">
                    <h2>📅 Next Session Plan</h2>
                    <div class="plan">
                        {next_plan}
                    </div>
                </div>
                
                <hr>
                <p style="color: #666; font-size: 12px;">
                    This is an automated report from your Moltbook Local Agent.<br>
                    To disable these reports, set ENABLE_EMAIL_REPORTS=false in your .env file.
                </p>
            </body>
            </html>
            """

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_USER
            msg["To"] = settings.EMAIL_TO

            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            log.success(f"Session report sent to {settings.EMAIL_TO}")

        except Exception as e:
            log.error(f"Failed to send email report: {e}")

    def send_failure_report(self, error_type: str, error_details: str):

        if not self.enabled:
            log.info("Email reports disabled, skipping failure notification")
            return

        try:
            subject = f"⚠️ Moltbook Agent Failure - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background: #f44336; color: white; padding: 20px; border-radius: 5px; }}
                    .error-box {{ background: #ffebee; padding: 15px; margin: 20px 0; border-left: 4px solid #f44336; border-radius: 3px; }}
                    .details {{ background: #f4f4f4; padding: 15px; margin: 20px 0; border-radius: 3px; font-family: monospace; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>⚠️ Moltbook Agent Session Failed</h1>
                    <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="error-box">
                    <h2>❌ Error Type: {error_type}</h2>
                </div>
                
                <div class="details">
                    <h3>Error Details:</h3>
                    <p>{error_details}</p>
                </div>
                
                <div style="margin-top: 30px; padding: 15px; background: #fff3cd; border-radius: 3px;">
                    <h3>💡 What to do:</h3>
                    <ul>
                        <li>Check if Moltbook API is online: <a href="https://moltbook.com">https://moltbook.com</a></li>
                        <li>Verify your API key in .env file</li>
                        <li>Check agent.log for detailed error messages</li>
                        <li>The agent will automatically retry on the next scheduled run</li>
                    </ul>
                </div>
                
                <hr>
                <p style="color: #666; font-size: 12px;">
                    This is an automated failure notification from your Moltbook Local Agent.<br>
                    Next scheduled run will attempt to reconnect.
                </p>
            </body>
            </html>
            """

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_USER
            msg["To"] = settings.EMAIL_TO

            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            log.success(f"Failure notification sent to {settings.EMAIL_TO}")

        except Exception as e:
            log.error(f"Failed to send failure notification: {e}")
