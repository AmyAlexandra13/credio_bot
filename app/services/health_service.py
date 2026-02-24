class HealthService:
    @staticmethod
    def get_status() -> dict:
        return {
            "status": "ok",
            "app": "credio-bot"
        }
