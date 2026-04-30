FROM teledev/tantrik:base_nbgrader

WORKDIR /srv/nbgrader/jupyterhub

RUN apt-get update && apt-get -y upgrade && \
    apt-get install -y build-essential libmysqlclient-dev && \
    apt-get install -y pkg-config iputils-ping openssh-client nano


RUN npm uninstall -g configurable-http-proxy \
    && npm install -g configurable-http-proxy@4.6.1

RUN pip install tensorflow seaborn statsmodels mysqlclient

COPY setup_pages/api.py /srv/nbgrader/nbgrader/nbgrader/apps/api.py
COPY setup_pages/generate_feedback.py /srv/nbgrader/nbgrader/nbgrader/converters/generate_feedback.py
COPY setup_pages/handlers.py /srv/nbgrader/nbgrader/nbgrader/server_extensions/assignment_list/handlers.py
COPY setup_pages/manage_assignments.tpl /srv/nbgrader/nbgrader/nbgrader/server_extensions/formgrader/templates/manage_assignments.tpl
COPY setup_pages/native-login.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/native-login.html
COPY setup_pages/page.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/page.html
COPY setup_pages/signup.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/signup.html
COPY setup_pages/users.py /usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers/users.py
COPY setup_pages/groups.py /usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers/groups.py
COPY setup_pages/validategradescore.py /srv/nbgrader/nbgrader/nbgrader/preprocessors/validategradescore.py
# COPY srv/nbgrader/jupyterhub /srv/nbgrader/jupyterhub
# COPY filemanager.py /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/filemanager.py
# COPY handlers.py /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/handlers.py
# COPY manager.py /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/manager.py
# COPY page_config.json /usr/etc/jupyter/labconfig/page_config.json
# COPY serverextension.py /usr/local/lib/python3.10/dist-packages/jupyter_server/extension/serverextension.py
# COPY labextensions.py /usr/local/lib/python3.10/dist-packages/jupyterlab/labextensions.py
# COPY apihandlers.py /srv/nbgrader/nbgrader/nbgrader/server_extensions/formgrader/apihandlers.py
# COPY tantrik.png /usr/local/share/jupyterhub/static/images/jupyterhub-80.png

WORKDIR /srv/nbgrader/nbgrader

# # Only in Teacher setup

RUN ["jupyter", "labextension", "enable", "--level=sys_prefix", "@jupyter/nbgrader:assignment-list"]


COPY setup_pages/setup_script.sh /usr/local/bin/setup_script.sh
RUN chmod +x /usr/local/bin/setup_script.sh

WORKDIR /srv/nbgrader/jupyterhub

EXPOSE 8000
#EXPOSE 8579

CMD ["/bin/bash", "-c", "/usr/local/bin/setup_script.sh  && exec /usr/local/bin/jupyterhub"]
# CMD ["/bin/bash", "-c", "/usr/local/bin/setup_script.sh && exec /usr/local/bin/jupyterhub && source .venv/bin/activate && python /home/tele/Music/Tantrik_Testcenter/singleevaluation.py"]