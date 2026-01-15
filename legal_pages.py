from nicegui import ui, app

def init_legal_pages():
    
    @ui.page('/terms')
    def terms_of_service():
        with ui.column().classes('w-full max-w-4xl mx-auto p-8'):
            ui.markdown("""
            # Terms of Service
            
            **Last Updated:** January 2026

            ## 1. Introduction
            Welcome to Skim. By accessing or using our website, you agree to be bound by these Terms of Service.

            ## 2. Use of Service
            Our service is provided for educational and research purposes. You agree not to misuse the service or help anyone else do so.

            ## 3. Account
            To access certain features, you may be required to create an account. You are responsible for maintaining the confidentiality of your account information.

            ## 4. Termination
            We reserve the right to suspend or terminate your access to our service at our sole discretion, without notice, for conduct that we believe violates these Terms.

            ## 5. Disclaimer
            The service is provided "as is" without warranties of any kind. We do not guarantee that the service will be error-free or uninterrupted.

            ## 6. Contact
            If you have any questions about these Terms, please contact us at support@example.com.
            """)
            ui.link('Back to Home', '/')

    @ui.page('/privacy')
    def privacy_policy():
        with ui.column().classes('w-full max-w-4xl mx-auto p-8'):
            ui.markdown("""
            # Privacy Policy
            
            **Last Updated:** January 2026

            ## 1. Information We Collect
            We collect information you provide directly to us, such as when you create an account, specifically your **email address** and **username**. We use this information solely for authentication and user profile management.

            ## 2. How We Use Information
            We use your information to:
            - Provide, maintain, and improve our services.
            - Process your registration and login.
            - Communications regarding your account.

            ## 3. Data Sharing
            We do not share your personal information with third parties except as required by law or to protect our rights.

            ## 4. Security
            We take reasonable measures to help protect information about you from loss, theft, misuse, and unauthorized access.

            ## 5. Your Rights
            You may update or correct your account information at any time by logging into your account settings.

            ## 6. Contact
            If you have any questions about this Privacy Policy, please contact us at support@example.com.
            """)
            ui.link('Back to Home', '/')
