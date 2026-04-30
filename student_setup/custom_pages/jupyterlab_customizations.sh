#disabled rename,delete,file creations
mv /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/filemanager.py /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/filemanager.py.org
cp filemanager.py /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/filemanager.py

#disabled upload,new directory
mv /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/handlers.py /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/handlers.py.org
cp handlers.py /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/handlers.py

#disabled new file creation
mv /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/manager.py /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/manager.py.org
cp manager.py /usr/local/lib/python3.10/dist-packages/jupyter_server/services/contents/manager.py

#disabled extensions
mv /usr/etc/jupyter/labconfig/page_config.json /usr/etc/jupyter/labconfig/page_config.json.org
cp page_config.json /usr/etc/jupyter/labconfig/page_config.json

# #Menu customizations
# if [ ! -d "/usr/local/share/jupyter/lab/schemas/@jupyterlab.org" ]; then
#   mv /usr/local/share/jupyter/lab/schemas/@jupyterlab /usr/local/share/jupyter/lab/schemas/@jupyterlab.org
# fi
# cp -r @jupyterlab /usr/local/share/jupyter/lab/schemas/

#disabled list and disable extensions
mv /usr/local/lib/python3.10/dist-packages/jupyter_server/extension/serverextension.py /usr/local/lib/python3.10/dist-packages/jupyter_server/extension/serverextension.py.org
cp serverextension.py /usr/local/lib/python3.10/dist-packages/jupyter_server/extension/serverextension.py

#disabled develop,build,watch,list,lock,unlock,install,uninstall extensions
mv /usr/local/lib/python3.10/dist-packages/jupyterlab/labextensions.py /usr/local/lib/python3.10/dist-packages/jupyterlab/labextensions.py.org
cp labextensions.py /usr/local/lib/python3.10/dist-packages/jupyterlab/labextensions.py

# if [ ! -d "/usr/local/share/jupyter/lab/schemas/@jupyterlab.org" ]; then
#   mv /usr/local/share/jupyter/lab/schemas/@jupyterlab /usr/local/share/jupyter/lab/schemas/@jupyterlab.org
# fi
# cp -r @jupyterlab /usr/local/share/jupyter/lab/schemas/
#formgrader
mv /srv/nbgrader/nbgrader/nbgrader/server_extensions/formgrader/apihandlers.py /srv/nbgrader/nbgrader/nbgrader/server_extensions/formgrader/apihandlers.py.org
cp apihandlers.py /srv/nbgrader/nbgrader/nbgrader/server_extensions/formgrader/apihandlers.py

# #LOGIN PAGE
# mv /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/native-login.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/native-login.html.org
# cp native-login.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/native-login.html

# #signup
# mv /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/signup.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/signup.html.org
# cp signup.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/signup.html

# #changepassword
# mv /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/page.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/page.html.org
# cp page.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/page.html

#logo
cp tantrik.png /usr/local/share/jupyterhub/static/images/jupyterhub-80.png
