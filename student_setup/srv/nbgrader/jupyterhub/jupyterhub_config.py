c = get_config()

import os,sys, nativeauthenticator
sys.path.append('/srv/nbgrader/jupyterhub')

# from custom_native_auth import JSONBasedNativeAuthenticator
c.JupyterHub.authenticator_class = 'native'
# c.JupyterHub.authenticator_class = JSONBasedNativeAuthenticator
from block_password import BlockUntilPasswordChange

from jupyterhub.handlers.base import BaseHandler
from tornado import web
from jupyterhub.apihandlers.users import AssignmentsPage

class GPUorchestratorPage(BaseHandler):

    @web.authenticated
    async def get(self):
        username = self.current_user.name

        try:
            self.log.debug(f"[GPUPage] Fetching courses for user: {username}")

            user = self.find_user(username)
            if user and user.orm_user:
                courses = [
                    g.name.replace("nbgrader-", "")
                    for g in user.orm_user.groups
                ]
                self.log.info(f"[GPUPage] Courses for {username}: {courses}")
            else:
                self.log.warning(f"[GPUPage] No ORM user found for: {username}")
                courses = []

        except Exception as e:
            self.log.exception(f"[GPUPage] Error fetching courses for {username}: {e}")
            courses = []

        # ------------------------------
        # Render template
        # ------------------------------
        try:
            self.log.debug(f"[GPUPage] Rendering demo.html for {username}")

            html = self.render_template(
                "demo.html",
                user=self.current_user,
                courses=courses,
                sync=True
            )

            self.set_header("Content-Type", "text/html; charset=utf-8")
            self.finish(html)

            self.log.info(f"[GPUPage] Successfully rendered demo.html for {username}")

        except Exception as e:
            self.log.exception(f"[GPUPage] Template rendering failed for {username}: {e}")
            self.set_status(500)
            self.finish("Internal server error while rendering page.")


c.JupyterHub.extra_handlers = [
    # (r"/hub/login.*", BlockedDayLoginHandler),
    (r"/assignmentlist/?", GPUorchestratorPage),
    (r"/assignments", AssignmentsPage),
    # (r"/force-change-password", BlockUntilPasswordChange),
]

# async def check_password_change(spawner):
#     user = spawner.user
#     db_user = spawner.authenticator.db.query(
#         spawner.authenticator.user_model
#     ).filter_by(name=user.name).first()

#     if not db_user.password_changed:
#         raise Exception("PASSWORD_CHANGE_REQUIRED")
    
# c.Spawner.pre_spawn_hook = check_password_change
# c.NativeAuthenticator.force_password_change = True
c.JupyterHub.template_paths = [f"{os.path.dirname(nativeauthenticator.__file__)}/templates/"]
c.Authenticator.admin_users = {'tele'}
c.NativeAuthenticator.open_signup = True
c.ServerApp.allow_origin = '*'
c.Authenticator.refresh_user = True  # already true by default
c.JupyterHub.refresh_users = True
c.JupyterHub.cleanup_servers = True
c.JupyterHub.shutdown_on_logout = True
c.JupyterHub.generate_tokens = True
c.JupyterHub.cookie_max_age_days = 0.2 # 4.8 hours
# c.JupyterHub.cookie_max_age_days = 0.000694 # 1 minute
c.JupyterHub.logout_redirect_url = '/hub/login'
c.GenerateFeedback.hide_autograder_tests = True


# c.JupyterHub.log_level = 'DEBUG'
# c.JupyterHub.extra_log_file = '/var/log/jupyterhub/nbgrader_debug.log'

# c.JupyterHub.db_url = "mysql+mysqldb://dockeruser:Tele123$@10.11.51.201:3306/student_jupyterhub"

# c.JupyterHub.default_url = '/hub/assignmentlist'
c.JupyterHub.default_url = '/hub/home'
c.JupyterHub.redirect_to_server = True

c.ServerApp.jpserver_extensions = {}
c.LabApp.expose_app_in_browser = False
c.LabApp.build = False

# Our user list
c.Authenticator.allowed_users = [
    'student1',
    'grader-course101',
    'grader-course123',
    # 'grader-demo',
    'tele',
    # 'grader-demo1',
    # 'grader-class',
    # 'grader-ps1',
    # 'grader-ps2',
    # 'grader-ps3',
    # 'grader-ps7',
    'grader-al',
]

# instructor1 and instructor2 have access to different shared servers.
# Note that groups providing access to the formgrader *must* start with
# 'formgrade-', and groups providing access to course materials *must*
# start with 'nbgrader-' in order for nbgrader to work correctly.
c.JupyterHub.load_groups = {
    'instructors': [
    ],
    'formgrade-course101': [
        'grader-course101',
    ],
    'formgrade-course123': [
        'grader-course123',
    ],
    # 'formgrade-demo': [
    #     'grader-demo',
    # ],
    'nbgrader-course101': [
        'student1',
    ],
    'nbgrader-course123': [
        'student1',
    ],  
    # 'nbgrader-demo': [
    #     'student1',
    # ], 
    # 'formgrade-demo1': [
    #     'grader-demo1',
    # ],
    # 'nbgrader-demo1': [
    #     'student1',
    # ],
    # 'formgrade-class': [
    #     'grader-class',
    # ],
    # 'nbgrader-class': [
    #     'student1',
    # ],
    # 'formgrade-ps1': [
    #     'grader-ps1',
    # ],
    # 'nbgrader-ps1': [
    #     'student1',
    # ],
    # 'formgrade-ps2': [
    #     'grader-ps2',
    # ],
    # 'nbgrader-ps2': [
    #     'student1',
    # ],
    # 'formgrade-ps3': [
    #     'grader-ps3',
    # ],
    # 'nbgrader-ps3': [
    #     'student1',
    # ],
    # 'formgrade-ps7': [
    #     'grader-ps7',
    # ],
    # 'nbgrader-ps7': [
    #     'student1',
    # ],
    'formgrade-al': [
        'grader-al',
    ],
    'nbgrader-al': [
        'student1',
    ],
}

c.JupyterHub.load_roles = roles = [
    {
        'name': 'instructor',
        'groups': ['instructors'],
        'scopes': [
            # these are the scopes required for the admin UI
            'admin:users',
            'admin:servers',
        ],
    },
    # The class_list extension needs permission to access services
    {
        'name': 'server',
        'scopes': [
            'inherit',
            # in JupyterHub 2.4, this can be a list of permissions
            # greater than the owner and the result will be the intersection;
            # until then, 'inherit' is the only way to have variable permissions
            # for the server token by user
            # "access:services",
            # "list:services",
            # "read:services",
            # "users:activity!user",
            # "access:servers!user",
        ],
    },
]
for course in ['course101', 'course123', 'al']:
    # access to formgrader
    roles.append(
        {
            'name': f'formgrade-{course}',
            'groups': [f'formgrade-{course}'],
            'scopes': [
                f'access:services!service={course}',
            ],
        }
    )
    # access to course materials
    roles.append(
        {
            'name': f'nbgrader-{course}',
            'groups': [f'nbgrader-{course}'],
            'scopes': [
                # access to the services API to discover the service(s)
                'list:services',
                f'read:services!service={course}',
            ],
        }
    )


# Start the notebook server as a service. The port can be whatever you want
# and the group has to match the name of the group defined above.
c.JupyterHub.services = [
    {
        'name': 'al',
        'url': 'http://127.0.0.1:10002',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-al',
        'cwd': '/home/grader-al',
        'environment': {
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': 'naZTTuTF0wa2mcWa',
    },


    # {
    #     'name': 'class',
    #     'url': 'http://127.0.0.1:10001',
    #     'command': [
    #         'jupyterhub-singleuser',
    #         '--debug',
    #     ],
    #     'user': 'grader-class',
    #     'cwd': '/home/grader-class',
    #     'environment': {
    #         'JUPYTERHUB_DEFAULT_URL': '/lab'
    #     },
    #     'api_token': 'c6zb8mA3VsCdDfBL',
    # },

    # {
    #     'name': 'demo1',
    #     'url': 'http://127.0.0.1:10000',
    #     'command': [
    #         'jupyterhub-singleuser',
    #         '--debug',
    #     ],
    #     'user': 'grader-demo1',
    #     'cwd': '/home/grader-demo1',
    #     'environment': {
    #         'JUPYTERHUB_DEFAULT_URL': '/lab'
    #     },
    #     'api_token': 'QCNTvbgMbYrBihFt',
    # },

    {
        'name': 'course101',
        'url': 'http://127.0.0.1:9999',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-course101',
        'cwd': '/home/grader-course101',
        'environment': {
            # specify lab as default landing page
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': 'fd6e0db39e534f6e91e415c01643cf3f',
    },
    {
        'name': 'course123',
        'url': 'http://127.0.0.1:9998',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-course123',
        'cwd': '/home/grader-course123',
        'environment': {
            # specify lab as default landing page
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': '',
    },
    # {
    #     'name': 'demo',
    #     'url': 'http://127.0.0.1:9997',
    #     'command': [
    #         'jupyterhub-singleuser',
    #         '--debug',
    #     ],
    #     'user': 'grader-demo',
    #     'cwd': '/home/grader-demo',
    #     'environment': {
    #         # specify lab as default landing page
    #         'JUPYTERHUB_DEFAULT_URL': '/lab'
    #     },
    #     'api_token': '',
    # },
]

# c.JupyterHub.services.append(
#     {
#         "name": "idle-culler",
#         "command": [
#             "/usr/bin/python3.10",
#             "-m",
#             "jupyterhub_idle_culler",
#             "--timeout=18000",          # 1 minute idle
#             "--cull-every=18000",       # check every 2 minutes
#             "--remove-named-servers",
#             "--cull-users=False",    # DO NOT delete users
#             "--max-age=18000",
#         ],
#         "admin": True,
#     }
# )
