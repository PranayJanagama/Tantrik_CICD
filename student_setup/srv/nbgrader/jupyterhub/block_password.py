from jupyterhub.handlers import BaseHandler

class BlockUntilPasswordChange(BaseHandler):
    async def prepare(self):
        user = self.current_user
        if user:
            db_user = self.authenticator.db.query(
                self.authenticator.user_model
            ).filter_by(name=user.name).first()

            if not db_user.password_changed and self.request.uri != "/force-change-password":
                self.redirect("/force-change-password")