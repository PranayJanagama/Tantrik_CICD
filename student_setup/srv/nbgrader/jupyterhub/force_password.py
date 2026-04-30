from tornado import web
from jupyterhub.handlers import BaseHandler

class ForcePasswordChangeHandler(BaseHandler):
    async def get(self):
        user = self.current_user
        if not user:
            return self.redirect('/hub/login')

        self.render("force_password_change.html")

    async def post(self):
        user = self.current_user
        new_password = self.get_argument("new_password")

        # update password using NativeAuthenticator API
        auth = self.authenticator
        await auth.change_password(user.name, new_password)

        # mark password as changed (IMPORTANT)
        auth.db.query(auth.user_model).filter_by(name=user.name).update({
            "password_changed": True
        })
        auth.db.commit()

        self.redirect('/hub/home')