# if virtual environment /opt/jupyterhub/lib/python3.10/site-packages/jupyterhub/apihandlers/users.py
# normal setup /usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers/users.py demo
"""User handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
from nbgrader.api import Gradebook
import inspect
import json
import sys
from datetime import timedelta, timezone, datetime
import random
import string
import json
if sys.version_info >= (3, 10):
    from contextlib import aclosing
else:
    from async_generator import aclosing
import subprocess
# from flask import jsonify

from dateutil.parser import parse as parse_date
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload, raiseload, selectinload  # noqa
from tornado import web
from tornado.iostream import StreamClosedError
from .. import orm, scopes
from ..roles import assign_default_roles
from ..scopes import needs_scope
from ..user import User
from ..utils import (
    isoformat,
    iterate_until,
    maybe_future,
    url_escape_path,
    url_path_join,
    utcnow,
)
from .base import APIHandler
import os
from nbgrader.apps import NbGraderAPI
from traitlets.config import Config
import base64
import sqlite3
import requests
from urllib.parse import urljoin, urlencode
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
import httpx
import pytz
UPLOAD_FOLDER = '/srv/manage_assignments/uploaded_files/'
TESTCENTER_URL = 'http://172.168.15.216:8582'
secret_key = "key123$"
api_access_token = '831f91sde70fdb411as2fc3224eb12904de307f8d6e'
# server = 225 

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class SelfAPIHandler(APIHandler):
    """Return the authenticated user's model

    Based on the authentication info. Acts as a 'whoami' for auth tokens.
    """

    async def get(self):
        user = self.current_user
        if user is None:
            raise web.HTTPError(403)

        _added_scopes = set()
        if isinstance(user, orm.Service):
            # ensure we have the minimal 'identify' scopes for the token owner
            identify_scopes = scopes.identify_scopes(user)
            get_model = self.service_model
        else:
            identify_scopes = scopes.identify_scopes(user.orm_user)
            get_model = self.user_model

        # ensure we have permission to identify ourselves
        # all tokens can do this on this endpoint
        for scope in identify_scopes:
            if scope not in self.expanded_scopes:
                _added_scopes.add(scope)
                self.expanded_scopes |= {scope}
        if _added_scopes:
            # re-parse with new scopes
            self.parsed_scopes = scopes.parse_scopes(self.expanded_scopes)

        model = get_model(user)

        # add session_id associated with token
        # added in 2.0
        # token_id added in 5.0
        token = self.get_token()
        if token:
            model["token_id"] = token.api_id
            model["session_id"] = token.session_id
        else:
            model["token_id"] = None
            model["session_id"] = None

        # add scopes to identify model,
        # but not the scopes we added to ensure we could read our own model
        model["scopes"] = sorted(self.expanded_scopes.difference(_added_scopes))
        self.write(json.dumps(model))

class HelloAPIHandler(APIHandler):
    def get(self, username):
        data={'message':f'Hello {username}'}
        self.finish(json.dumps(data))

class TotalStudentsAPIHandler(APIHandler):

    def decrypt(self,encoded_token):

        try:
            encrypted_bytes = base64.b64decode(encoded_token)
            result = ''
            for i in range(len(encrypted_bytes)):
                char_code = encrypted_bytes[i]
                key_code = ord(secret_key[i % len(secret_key)])
                result += chr(char_code ^ key_code)
            #print(f"{result}")
            return result.split('$$$')[1]
        except Exception as e:
            print("Error while decrypting token: {}", str(e))
            return e

    def get(self):
        access_token = self.get_body_argument('access_token')
        key = self.decrypt(access_token)
        value=api_access_token
        if key == value:
            try:
                course_name = self.get_body_argument("course_name")
                # print(f"{course_name}")
                if course_name is None:
                    raise "Course is None!"
                db_path = f"/srv/nbgrader/jupyterhub/jupyterhub.sqlite"
                if os.path.isfile(db_path):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    group = f"nbgrader-{course_name}"
                    cursor.execute("SELECT count(*) FROM users u join user_group_map ug on ug.user_id = u.id join groups g on g.id = ug.group_id WHERE g.name= ?", (group,))
                    studentscount = cursor.fetchone()
                    if studentscount is None:
                        self.write(json.dumps({"total": 0, "message": "Error in getting count from DB"}))
                    self.write(json.dumps({"total":studentscount[0],"message":"Count fetched successfully"}))
                else:
                    self.write(json.dumps({"total":0, "message":"DB file not found"}))
            except Exception as e: 
                self.write(json.dumps({"total":0, "message":str(e)}))
        else:
            self.write(json.dumps({"error":"Invalid access_token"}))
            self.set_status(403)  # Set a forbidden status for invalid tokens

class ActiveStudentsAPIHandler(APIHandler):

    def decrypt(self,encoded_token):

        try:
            encrypted_bytes = base64.b64decode(encoded_token)
            result = ''
            for i in range(len(encrypted_bytes)):
                char_code = encrypted_bytes[i]
                key_code = ord(secret_key[i % len(secret_key)])
                result += chr(char_code ^ key_code)
            #print(f"{result}")
            return result.split('$$$')[1]
        except Exception as e:
            print("Error while decrypting token: {}", str(e))
            return e

    def get(self):
        access_token = self.get_body_argument('access_token')
        key = self.decrypt(access_token)
        value=api_access_token
        if key == value:
            try:
                course_name = self.get_body_argument("course_name")
                if course_name is None:
                    raise "Course is None!"
                db_path = f"/srv/nbgrader/jupyterhub/jupyterhub.sqlite"
                if os.path.isfile(db_path):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    now = datetime.utcnow()
                    start_of_today_ist = now - timedelta(hours=5, minutes=30)
                    end_of_today_ist = start_of_today_ist + timedelta(days=1)

                    # Convert to UTC format
                    start_of_today_utc = start_of_today_ist.strftime('%Y-%m-%d %H:%M:%S')
                    end_of_today_utc = end_of_today_ist.strftime('%Y-%m-%d %H:%M:%S')

                    group = f"nbgrader-{course_name}"
                    cursor.execute("SELECT count(*) FROM users u join user_group_map ug on ug.user_id = u.id join groups g on g.id = ug.group_id WHERE g.name=? and u.last_activity BETWEEN ? AND ?;", (group,start_of_today_utc,end_of_today_utc,))
                    activecount = cursor.fetchone()
                    if activecount is None:
                        self.write(json.dumps({"total":0, "message":"Error in getting count from DB"}))
                    self.write(json.dumps({"total":activecount[0],"message":"Count fetched successfully"}))
                else:
                    self.write(json.dumps({"total":0, "message":"DB file not found"}))
            except Exception as e: 
                    self.write(json.dumps({"total":0, "message":str(e)}))
        else:
            self.write(json.dumps({"error":"Invalid access_token"}))
            self.set_status(403)  # Set a forbidden status for invalid tokens        

class SubmittedCountAPIHandler(APIHandler):

    def decrypt(self,encoded_token):

        try:
            encrypted_bytes = base64.b64decode(encoded_token)
            result = ''
            for i in range(len(encrypted_bytes)):
                char_code = encrypted_bytes[i]
                key_code = ord(secret_key[i % len(secret_key)])
                result += chr(char_code ^ key_code)
            #print(f"{result}")
            return result.split('$$$')[1]
        except Exception as e:
            print("Error while decrypting token: {}", str(e))
            return e

    async def get(self):
        # course_name = self.get_body_argument('course_name')
        # assignment_name = self.get_body_argument('assignment_name')
        # access_token = self.get_body_argument('access_token')
        course_name = self.get_argument('course_name')
        assignment_name = self.get_argument('assignment_name')
        access_token = self.get_argument('access_token')

        key = self.decrypt(access_token)
        value=api_access_token
        if key == value:
            if course_name is not None and assignment_name is not None:
                try:
                    config = Config()
                    config.CourseDirectory.course_id = course_name
                    config.CourseDirectory.root = f'/home/grader-{course_name}/{course_name}'
                    api = NbGraderAPI(config=config)
                    students = api.get_submitted_students(assignment_name)
                    self.write(json.dumps({"count":len(students),"message":"count retrieved successfully"}))
                except ValueError as e:
                    self.write(json.dumps({"count":0,"message":str(e)}))
            else:
                self.write(json.dumps({"count":0,"message":"course or assignment is None"}))
        else:
            self.write(json.dumps({"error":"Invalid access_token"}))
            self.set_status(403)  # Set a forbidden status for invalid tokens        


class FeedbackFileAPIHandler(APIHandler):

    def decrypt(self,encoded_token):

        try:
            encrypted_bytes = base64.b64decode(encoded_token)
            result = ''
            for i in range(len(encrypted_bytes)):
                char_code = encrypted_bytes[i]
                key_code = ord(secret_key[i % len(secret_key)])
                result += chr(char_code ^ key_code)
            #print(f"{result}")
            return result.split('$$$')[1]
        except Exception as e:
            print("Error while decrypting token: {}", str(e))
            return e

    async def post(self):
        path = self.get_body_argument("path")
        print("fedback  ",path)
        access_token = self.get_body_argument('access_token')
        key = self.decrypt(access_token)
        value=api_access_token
        if key == value:
            for file in os.listdir(path):
                if file.endswith(".html"):
                    filename = file
                    break

            safe_filename = os.path.basename(filename)
            file_path = os.path.join(path, safe_filename)
            # print(file_path)
            if not os.path.isfile(file_path):
                self.write(json.dumps({"error": "File not found"}))
                self.set_status(404)

            try:
                file=os.path.join(path, safe_filename)
                with open(file, 'rb') as f:
                    contents = f.read()
                text=contents.decode('utf-8')
                self.write(json.dumps({"text":f"{text}"}))
            except Exception:
                self.write(json.dumps({"error": "Error serving file"}))
                self.set_status(500)
        else:
            self.write(json.dumps({"error":"Invalid access_token"}))
            self.set_status(403)  # Set a forbidden status for invalid tokens        

class ReleaseAssignmentAPIHandler(APIHandler):

    def decrypt(self,encoded_token):

        try:
            encrypted_bytes = base64.b64decode(encoded_token)
            result = ''
            for i in range(len(encrypted_bytes)):
                char_code = encrypted_bytes[i]
                key_code = ord(secret_key[i % len(secret_key)])
                result += chr(char_code ^ key_code)
            #print(f"{result}")
            return result.split('$$$')[1]
        except Exception as e:
            print("Error while decrypting token: {}", str(e))
            return e


    async def post(self):
        coursename = self.get_body_argument('course_name')
        assignmentname = self.get_body_argument('assignment_name')
        access_token = self.get_body_argument('access_token')
        key = self.decrypt(access_token)
        value=api_access_token
        if key == value:
    
            try:
                notebook_path = f"/home/grader-{coursename}/{coursename}"
                config = Config()
                config.CourseDirectory.root = notebook_path  # Set the root path
                config.CourseDirectory.course_id = coursename
                config.CourseDirectory.groupshared = True
                api = NbGraderAPI(config=config)
                result = api.release_assignment(assignmentname)
                # print(result)
                self.write(json.dumps({'message': f'assignment released successfully'}))
                self.set_status(200)
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                self.write(json.dumps({'message': f'Error in release assignment: {str(e)}'}))
                self.set_status(500)
        else:
            self.write(json.dumps({"error":"Invalid access_token"}))
            self.set_status(403)  # Set a forbidden status for invalid tokens


class UnreleaseAssignmentAPIHandler(APIHandler):

    def decrypt(self,encoded_token):

        try:
            encrypted_bytes = base64.b64decode(encoded_token)
            result = ''
            for i in range(len(encrypted_bytes)):
                char_code = encrypted_bytes[i]
                key_code = ord(secret_key[i % len(secret_key)])
                result += chr(char_code ^ key_code)
            #print(f"{result}")
            return result.split('$$$')[1]
        except Exception as e:
            print("Error while decrypting token: {}", str(e))
            return e


    async def post(self):
        coursename = self.get_body_argument('course_name')
        assignmentname = self.get_body_argument('assignment_name')
        access_token = self.get_body_argument('access_token')
        key = self.decrypt(access_token)
        value=api_access_token
        if key == value:
    
            try:
                notebook_path = f"/home/grader-{coursename}/{coursename}"
                config = Config()
                config.CourseDirectory.root = notebook_path  # Set the root path
                config.CourseDirectory.course_id = coursename
                config.CourseDirectory.groupshared = True
                api = NbGraderAPI(config=config)
                result = api.unrelease(assignmentname)
                # print(result)
                self.write(json.dumps({'message': f'assignment unreleased successfully'}))
                self.set_status(200)
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                self.write(json.dumps({'message': f'Error in unrelease assignment: {str(e)}'}))
                self.set_status(500)
        else:
            self.write(json.dumps({"error":"Invalid access_token"}))
            self.set_status(403)  # Set a forbidden status for invalid tokens


class GenerateAssignmentAPIHandler(APIHandler):

    def decrypt(self,encoded_token):

        try:
            encrypted_bytes = base64.b64decode(encoded_token)
            result = ''
            for i in range(len(encrypted_bytes)):
                char_code = encrypted_bytes[i]
                key_code = ord(secret_key[i % len(secret_key)])
                result += chr(char_code ^ key_code)
            #print(f"{result}")
            return result.split('$$$')[1]
        except Exception as e:
            print("Error while decrypting token: {}", str(e))
            return e

    def create_assignment_dir(self,assignmentpath, user, coursename, assignmentname):
        home = f"/home/{user}"
        #print(f"{user}")
        runas = f"sudo -u {user}"
        currdir = os.getcwd()
        #print("course name ",coursename)
        course = f"/home/{user}/{coursename}"
        #print("course dir ",course)
        try:
            os.chdir(home)
            subprocess.run(f"mkdir -p {assignmentpath}", shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while running the command: {e}")

        finally:
            os.chdir(currdir)

    async def post(self):
        coursename = self.get_body_argument('course_name')
        assignmentname = self.get_body_argument('assignment_name')
        access_token = self.get_body_argument('access_token')
        key = self.decrypt(access_token)
        value=api_access_token
        if key == value:
            if 'file' not in self.request.files:
                self.write(json.dumps({'message': 'No file part'}))
                self.set_status(400)
            #print(f"{self.request.files}")
            uploaded_files = self.request.files.get('file')
            #print(f"{uploaded_files}")
            file_info=uploaded_files[0]
            #print(f"{file_info}")
            filename=file_info['filename']
            #print("{filename}")
            body = file_info['body']
            try:
                user =  f'grader-{coursename}'
                #print(f"{user}")
                # Ensure the directory exists
                assignmentfolder = f'/home/grader-{coursename}/{coursename}/source/{assignmentname}/'
                self.create_assignment_dir(assignmentfolder,f'{user}',f'{coursename}',f'{assignmentname}')

                folder = os.path.join(UPLOAD_FOLDER, coursename)
                if not os.path.exists(folder):
                    os.mkdir(folder)

                file_path = os.path.join(folder, filename)
                with open(file_path, 'wb') as f:
                    f.write(body)  # Write the contents of the file

                runas = f"sudo -u {user}"
                subprocess.run(f"mv {file_path} {assignmentfolder}", shell=True, check=True)
                subprocess.run(f"chown -R  grader-{coursename}:grader-{coursename} {assignmentfolder}", shell=True, check=True)
                subprocess.run(f"chmod -R 744 {assignmentfolder}", shell=True, check=True)

                course = f"/home/{user}/{coursename}"
                notebook_path = f"/home/grader-{coursename}/{coursename}"
                config = Config()
                config.CourseDirectory.root = notebook_path  # Set the root path
                config.CourseDirectory.course_id = coursename
                config.CourseDirectory.groupshared= True
                api = NbGraderAPI(config=config)
                result = api.generate_assignment(assignmentname, force=True, create=True)
                print(result)
                self.write(json.dumps({"message": "assignment generated successfully"}))
                self.set_status(200)
            except Exception as e:
                self.write(json.dumps({"message": f"Error in generate assignment: {str(e)}"}))
                self.set_status(500)
        else:
            self.write(json.dumps({"error":"Invalid access_token"}))
            self.set_status(403)  # Set a forbidden status for invalid tokens

class AutogradeAPIHandler(APIHandler):
    
    def collect(self, course_name, assignment_name):
        print("collect")
        coursename = course_name
        assignmentname = assignment_name
        try:
            notebook_path = f"/home/grader-{coursename}/{coursename}"
            config = Config()
            config.CourseDirectory.root = notebook_path  # Set the root path
            config.CourseDirectory.course_id = coursename
            config.CourseDirectory.groupshared= True
            api = NbGraderAPI(config=config)
            result = api.collect(assignmentname, update=True)
            # print(result)
            print(f"message: collected successfully")
        except Exception as e:
            self.write(f"message: Error in collecting  assignment: {str(e)}")
            self.set_status(500)

    def autograde(self, course_name, assignment_name, server):

        coursename = course_name
        assignmentname = assignment_name

        try:
            notebook_path = f"/home/grader-{coursename}/{coursename}"
            config = Config()
            config.CourseDirectory.root = notebook_path  # Set the root path
            config.CourseDirectory.course_id = coursename
            config.CourseDirectory.groupshared= True
            api = NbGraderAPI(config=config)
            students_list=api.get_submitted_students(assignmentname)
            db_path = os.path.join(notebook_path, 'gradebook.db')
            # for student in students_list:
            #     result = api.autograde(assignmentname, student, force=False, create=True)
            for student in students_list:
                try:
                    result = api.autograde(assignmentname, student, force=False, create=True)
                except Exception as e:
                    print(f"Error grading {student}: {e}. Trying with force=True.")
                    try:
                        result = api.autograde(assignmentname, student, force=True, create=True)
                    except Exception as e:
                        print(f"Error in autograding for {student}: {e}")
                        continue
                
                try:    
                    result = api.generate_feedback(assignmentname, student, force=True)
                except Exception as e:
                    print(f"Error grading {student}: {e}. Trying with force=True.")
                    try:
                        result = api.generate_feedback(assignmentname, student, force=True)
                    except Exception as e:
                        print(f"Error in generate feedback for {student}: {e}")
                        continue    
                try:  
                    result = api.release_feedback(assignmentname, student)
                except Exception as e:
                    print(f"Error grading {student}: {e}. Trying with force=True.")
                    try:
                        result = api.release_feedback(assignmentname, student)
                    except Exception as e:
                        print(f"Error in release feedback for {student}: {e}")
                        continue
                
                student_list = self.graded_students(db_path, assignmentname, student_id=student, server=server)

            # print(result)
            print(f"message: autograded successfully")
        except Exception as e:
            self.write(f"message: Error in autograding assignment: {str(e)}")
            self.set_status(500)

    
    def decrypt(self,encoded_token):
        try:
            encrypted_bytes = base64.b64decode(encoded_token)
            result = ''
            for i in range(len(encrypted_bytes)):
                char_code = encrypted_bytes[i]
                key_code = ord(secret_key[i % len(secret_key)])
                result += chr(char_code ^ key_code)
            #print(f"{result}")
            return result.split('$$$')[1]
        except Exception as e:
            print("Error while decrypting token: {}", str(e))
            return e


    def get_grade_of_student(self, db_path, assignment_name, student_id):
        if os.path.exists(db_path):
            with Gradebook(f'sqlite:///{db_path}') as gb:
                try:
                    submission =  gb.find_submission(assignment_name, student_id)
                    score_str = f"{int(submission.score)}/{int(submission.max_score)}" if submission.score is not None and submission.max_score is not None else "NG"
                    print("get_grade_of_student score", score_str)
                    return score_str
                except Exception as e:
                    print("get_grade_of_student error",str(e))
                    return 'NG'
    
    def graded_students(self, db_path, assignment_name, student_id, server):
        try:
            print("\n\n\n\ngraded_student\n\n\n", student_id,"\n\n\n")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            print("grade_student")
            cursor.execute("SELECT a.course_id,s.student_id,s.timestamp, s.id FROM submitted_assignment s join assignment a on a.id = s.assignment_id WHERE a.name = ? and s.student_id = ?", (assignment_name, student_id,))
            list_sub = cursor.fetchall()
            json_objects = []
            for entry in list_sub:
                json_object = {
                    "course": entry[0],
                    "assignment_name": assignment_name,
                    "student": entry[1],
                    "timestamp": entry[2],
                    "submit_id": entry[3],
                    "score": self.get_grade_of_student(db_path,assignment_name,entry[1]),
                    "server":server
                }
                try:
                    response = requests.post(f"{TESTCENTER_URL}/syncscore",data=json_object)
                    print("\n\n\n\n\n",json_object, response,"\n\n\n\n\n\n")
                    if response.status_code == 200:
                        print("grade submitted successfully",json_object["student"])
                    else:
                        print("grade submit not successfully",json_object["student"])
                except Exception as e:
                    print("get_graded_submissions+++++++++++",str(e))
            conn.close()
            return json_objects
        except Exception as e:
            print("get_graded_submissions+++++++++++",str(e))
            return e

    async def post(self):

        coursename = self.get_body_argument('course_name')
        assignmentname = self.get_body_argument('assignment_name')
        access_token = self.get_body_argument('access_token')
        server_number = self.get_body_argument('server_number')
        # server = server_number
        key = self.decrypt(access_token)
        value=api_access_token
        home = f"/home/grader-{coursename}"

        if key == value:
            try:
                self.collect(coursename, assignmentname)
                self.autograde(coursename, assignmentname, server=server_number)
                
                self.write(json.dumps({"message": "autograding completed successfully"}))
                self.set_status(200)
            except Exception as e:
                self.write(json.dumps({"message": f"Error in autograding assignment: {str(e)}"}))
                self.set_status(500)
        else:
            self.write(json.dumps({"error":"Invalid access_token"}))
            self.set_status(403)

class ReEvaluatingAPIHandler(APIHandler):
    
    def check_xsrf_cookie(self):
        """Override Tornado's XSRF check to skip validation for this endpoint."""
        return
    
    def collect(self, course_name, assignment_name):
        print("collect")
        coursename = course_name
        assignmentname = assignment_name
        try:
            notebook_path = f"/home/grader-{coursename}/{coursename}"
            config = Config()
            config.CourseDirectory.root = notebook_path  # Set the root path
            config.CourseDirectory.course_id = coursename
            config.CourseDirectory.groupshared= True
            api = NbGraderAPI(config=config)
            result = api.collect(assignmentname, update=True)
            # print(result)
            print(f"message: collected successfully")
        except Exception as e:
            self.write(f"message: Error in collecting  assignment: {str(e)}")
            self.set_status(500)

    def autograde(self, course_name, assignment_name, server, student_id):

        coursename = course_name
        assignmentname = assignment_name

        try:
            notebook_path = f"/home/grader-{coursename}/{coursename}"
            config = Config()
            config.CourseDirectory.root = notebook_path  # Set the root path
            config.CourseDirectory.course_id = coursename
            config.CourseDirectory.groupshared= True
            api = NbGraderAPI(config=config)
            students_list=api.get_submitted_students(assignmentname)
            db_path = os.path.join(notebook_path, 'gradebook.db')
            # for student in students_list:
            #     result = api.autograde(assignmentname, student, force=False, create=True)
            if student_id in students_list:
                try:
                    result = api.autograde(assignmentname, student_id, force=False, create=True)
                except Exception as e:
                    print(f"Error grading {student_id}: {e}. Trying with force=True.")
                    try:
                        result = api.autograde(assignmentname, student_id, force=True, create=True)
                    except Exception as e:
                        print(f"Error in autograding for {student_id}: {e}")
                        raise e
                try:    
                    result = api.generate_feedback(assignmentname, student_id, force=True)
                except Exception as e:
                    print(f"Error grading {student_id}: {e}. Trying with force=True.")
                    try:
                        result = api.generate_feedback(assignmentname, student_id, force=True)
                    except Exception as e:
                        print(f"Error in generate feedback for {student_id}: {e}")
                        raise e
                try:  
                    result = api.release_feedback(assignmentname, student_id)
                except Exception as e:
                    print(f"Error grading {student_id}: {e}. Trying with force=True.")
                    try:
                        result = api.release_feedback(assignmentname, student_id)
                    except Exception as e:
                        print(f"Error in release feedback for {student_id}: {e}")
                        raise e
                
                student_list = self.graded_students(db_path, assignmentname, student_id=student_id, server=server)
            else:
                raise "Student Not Found"
            # print(result)
            print(f"message: Re-Evaluation successfully")
        except Exception as e:
            self.write(f"message: Error While Evaluating")
            self.set_status(500)
            raise e

    
    def decrypt(self,encoded_token):
        try:
            encrypted_bytes = base64.b64decode(encoded_token)
            result = ''
            for i in range(len(encrypted_bytes)):
                char_code = encrypted_bytes[i]
                key_code = ord(secret_key[i % len(secret_key)])
                result += chr(char_code ^ key_code)
            #print(f"{result}")
            return result.split('$$$')[1]
        except Exception as e:
            print("Error while decrypting token: {}", str(e))
            return e


    def get_grade_of_student(self, db_path, assignment_name, student_id):
        if os.path.exists(db_path):
            with Gradebook(f'sqlite:///{db_path}') as gb:
                try:
                    submission =  gb.find_submission(assignment_name, student_id)
                    score_str = f"{int(submission.score)}/{int(submission.max_score)}" if submission.score is not None and submission.max_score is not None else "NG"
                    print("get_grade_of_student score", score_str)
                    return score_str
                except Exception as e:
                    print("get_grade_of_student error",str(e))
                    return 'NG'
    
    def graded_students(self, db_path, assignment_name, student_id, server):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            print("grade_student")
            cursor.execute("SELECT a.course_id,s.student_id,s.timestamp, s.id FROM submitted_assignment s join assignment a on a.id = s.assignment_id WHERE a.name = ? and s.student_id = ?", (assignment_name, student_id,))
            list_sub = cursor.fetchall()
            json_objects = []
            for entry in list_sub:
                json_object = {
                    "course": entry[0],
                    "assignment_name": assignment_name,
                    "student": entry[1],
                    "timestamp": entry[2],
                    "submit_id": entry[3],
                    "score": self.get_grade_of_student(db_path,assignment_name,entry[1]),
                    "server":server
                }
                try:
                    response = requests.post(f"{TESTCENTER_URL}/syncscore",data=json_object)
                    if response.status_code == 200:
                        print("grade submitted successfully",json_object["student"])
                    else:
                        print("grade submit not successfully",json_object["student"])
                except Exception as e:
                    print("get_graded_submissions+++++++++++",str(e))
            conn.close()
            return json_objects
        except Exception as e:
            print("get_graded_submissions+++++++++++",str(e))
            return e

    async def post(self):
        coursename = self.get_body_argument('course_name')
        assignmentname = self.get_body_argument('assignment_name')
        access_token = self.get_body_argument('access_token')
        server_number = self.get_body_argument('server')
        student = self.get_body_argument('student')
        # server = server_number
        key = self.decrypt(access_token)
        value=api_access_token
        home = f"/home/grader-{coursename}"     

        # if key == value:
        try:
            self.collect(coursename, assignmentname)
            self.autograde(coursename, assignmentname, server_number,student)
            
            self.write(json.dumps({"message": "Re-Evaluation completed successfully"}))
            self.set_status(200)
        except Exception as e:
            self.write(json.dumps({"message": f"Error in re-evaluating student: {str(e)}"}))
            self.set_status(500)
        # else:
        #     self.write(json.dumps({"error":"Invalid access_token"}))
        #     self.set_status(403)

class UserListAPIHandler(APIHandler):
    def _user_has_ready_spawner(self, orm_user):
        """Return True if a user has *any* ready spawners

        Used for filtering from active -> ready
        """
        user = self.users[orm_user]
        return any(spawner.ready for spawner in user.spawners.values())

    @needs_scope('list:users')
    def get(self):
        state_filter = self.get_argument("state", None)
        name_filter = self.get_argument("name_filter", None)
        sort = sort_by_param = self.get_argument("sort", "id")
        sort_direction = "asc"
        if sort[:1] == '-':
            sort_direction = "desc"
            sort = sort[1:]

        offset, limit = self.get_api_pagination()

        if sort in {"id", "name", "last_activity"}:
            sort_column = getattr(orm.User, sort)
        else:
            raise web.HTTPError(
                400,
                f"sort must be 'id', 'name', or 'last_activity', not '{sort_by_param}'",
            )

        # NULL is sorted inconsistently, so make it explicit
        if sort_direction == "asc":
            sort_order = (sort_column.is_not(None), sort_column.asc())
        elif sort_direction == "desc":
            sort_order = (sort_column.is_(None), sort_column.desc())
        else:
            # this can't happen, users don't specify direction
            raise ValueError(
                f"sort_direction must be 'asc' or 'desc', got '{sort_direction}'"
            )

        # post_filter
        post_filter = None

        # starting query
        query = self.db.query(orm.User)

        if state_filter in {"active", "ready"}:
            # only get users with active servers
            # an 'active' Spawner has a server record in the database
            # which means Spawner.server != None
            # it may still be in a pending start/stop state.
            # join filters out users with no Spawners
            query = (
                query
                # join filters out any Users with no Spawners
                .join(orm.Spawner, orm.User._orm_spawners)
                # this implicitly gets Users with *any* active server
                .filter(orm.Spawner.server != None)
                # group-by ensures the count is correct
                .group_by(orm.User.id)
            )
            if state_filter == "ready":
                # have to post-process query results because active vs ready
                # can only be distinguished with in-memory Spawner properties
                post_filter = self._user_has_ready_spawner

        elif state_filter == "inactive":
            # only get users with *no* active servers
            # as opposed to users with *any inactive servers*
            # this is the complement to the above query.
            # how expensive is this with lots of servers?
            query = (
                query.outerjoin(orm.Spawner, orm.User._orm_spawners)
                .outerjoin(orm.Server, orm.Spawner.server)
                .group_by(orm.User.id)
                .having(func.count(orm.Server.id) == 0)
            )
        elif state_filter:
            raise web.HTTPError(400, f"Unrecognized state filter: {state_filter!r}")

        # apply eager load options
        query = query.options(
            selectinload(orm.User.roles),
            selectinload(orm.User.groups),
            joinedload(orm.User._orm_spawners).joinedload(orm.Spawner.user),
            # raiseload here helps us make sure we've loaded everything in one query
            # but since we share a single db session, we can't do this for real
            # but it's useful in testing
            # raiseload("*"),
        )

        sub_scope = self.parsed_scopes['list:users']
        if sub_scope != scopes.Scope.ALL:
            if not set(sub_scope).issubset({'group', 'user'}):
                # don't expand invalid !server=x filter to all users!
                self.log.warning(
                    f"Invalid filter on list:user for {self.current_user}: {sub_scope}"
                )
                raise web.HTTPError(403)
            filters = []
            if 'user' in sub_scope:
                filters.append(orm.User.name.in_(sub_scope['user']))
            if 'group' in sub_scope:
                filters.append(
                    orm.User.groups.any(
                        orm.Group.name.in_(sub_scope['group']),
                    )
                )

            if len(filters) == 1:
                query = query.filter(filters[0])
            else:
                query = query.filter(or_(*filters))

        if name_filter:
            query = query.filter(orm.User.name.ilike(f'%{name_filter}%'))

        full_query = query
        query = query.order_by(*sort_order).offset(offset).limit(limit)

        user_list = []
        for u in query:
            if post_filter is None or post_filter(u):
                user_model = self.user_model(u)
                if user_model:
                    user_list.append(user_model)

        total_count = full_query.count()
        if self.accepts_pagination:
            data = self.paginated_model(user_list, offset, limit, total_count)
        else:
            query_count = query.count()
            if offset == 0 and total_count > query_count:
                self.log.warning(
                    f"Truncated user list in request that does not expect pagination. Processing {query_count} of {total_count} total users."
                )
            data = user_list

        self.write(json.dumps(data))
        # if testing with raiseload above, need expire_all to avoid affecting other operations
        # self.db.expire_all()

    @needs_scope('admin:users')
    async def post(self):
        data = self.get_json_body()
        if not data or not isinstance(data, dict) or not data.get('usernames'):
            raise web.HTTPError(400, "Must specify at least one user to create")

        usernames = data.pop('usernames')
        self._check_user_model(data)
        # admin is set for all users
        # to create admin and non-admin users requires at least two API requests
        admin = data.get('admin', False)
        if admin and not self.current_user.admin:
            raise web.HTTPError(403, "Only admins can grant admin permissions")

        to_create = []
        invalid_names = []
        for name in usernames:
            name = self.authenticator.normalize_username(name)
            if not self.authenticator.validate_username(name):
                invalid_names.append(name)
                continue
            user = self.find_user(name)
            if user is not None:
                self.log.warning(f"User {name} already exists")
            else:
                to_create.append(name)

        if invalid_names:
            if len(invalid_names) == 1:
                msg = f"Invalid username: {invalid_names[0]}"
            else:
                msg = "Invalid usernames: {}".format(', '.join(invalid_names))
            raise web.HTTPError(400, msg)

        if not to_create:
            raise web.HTTPError(409, "All %i users already exist" % len(usernames))

        created = []
        for name in to_create:
            user = self.user_from_username(name)
            if admin:
                user.admin = True
            assign_default_roles(self.db, entity=user)
            self.db.commit()
            try:
                await maybe_future(self.authenticator.add_user(user))
            except Exception as e:
                self.log.error(f"Failed to create user: {name}", exc_info=True)
                self.users.delete(user)
                raise web.HTTPError(400, f"Failed to create user {name}: {e}")
            else:
                created.append(user)

        self.write(json.dumps([self.user_model(u) for u in created]))
        self.set_status(201)


class UserAPIHandler(APIHandler):
    @needs_scope(
        'read:users',
        'read:users:name',
        'read:servers',
        'read:users:groups',
        'read:users:activity',
        'read:roles:users',
    )
    async def get(self, user_name):
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(404)
        model = self.user_model(user)
        # auth state will only be shown if the requester is an admin
        # this means users can't see their own auth state unless they
        # are admins, Hub admins often are also marked as admins so they
        # will see their auth state but normal users won't
        if 'auth_state' in model:
            model['auth_state'] = await user.get_auth_state()
        self.write(json.dumps(model))

    @needs_scope('admin:users')
    async def post(self, user_name):
        data = self.get_json_body()
        user = self.find_user(user_name)
        if user is not None:
            raise web.HTTPError(409, f"User {user_name} already exists")

        if data:
            self._check_user_model(data)
            if data.get('admin', False) and not self.current_user.admin:
                raise web.HTTPError(403, "Only admins can grant admin permissions")

        # create the user
        user = self.user_from_username(user_name)
        if data and data.get('admin', False):
            user.admin = data['admin']
            assign_default_roles(self.db, entity=user)
        self.db.commit()

        try:
            await maybe_future(self.authenticator.add_user(user))
        except Exception:
            self.log.error(f"Failed to create user: {user_name}", exc_info=True)
            # remove from registry
            self.users.delete(user)
            raise web.HTTPError(400, f"Failed to create user: {user_name}")

        self.write(json.dumps(self.user_model(user)))
        self.set_status(201)

    @needs_scope('delete:users')
    async def delete(self, user_name):
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(404)
        if user.name == self.current_user.name:
            raise web.HTTPError(400, "Cannot delete yourself!")
        if user.spawner._stop_pending:
            raise web.HTTPError(
                400,
                f"{user_name}'s server is in the process of stopping, please wait.",
            )
        if user.running:
            await self.stop_single_user(user)
            if user.spawner._stop_pending:
                raise web.HTTPError(
                    400,
                    f"{user_name}'s server is in the process of stopping, please wait.",
                )

        await maybe_future(self.authenticator.delete_user(user))

        await user.delete_spawners()

        # remove from registry
        self.users.delete(user)

        self.set_status(204)

    @needs_scope('admin:users')
    async def patch(self, user_name):
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(404)
        data = self.get_json_body()
        self._check_user_model(data)
        if 'name' in data and data['name'] != user_name:
            # check if the new name is already taken inside db
            if self.find_user(data['name']):
                raise web.HTTPError(
                    400,
                    "User {} already exists, username must be unique".format(
                        data['name']
                    ),
                )

        if not self.current_user.admin:
            if user.admin:
                raise web.HTTPError(403, "Only admins can modify other admins")
            if 'admin' in data and data['admin']:
                raise web.HTTPError(403, "Only admins can grant admin permissions")
        for key, value in data.items():
            value_s = "..." if key == "auth_state" else repr(value)
            self.log.info(
                f"{self.current_user.name} setting {key}={value_s} for {user.name}"
            )
            if key == 'auth_state':
                await user.save_auth_state(value)
            else:
                setattr(user, key, value)
                if key == 'admin':
                    assign_default_roles(self.db, entity=user)
        self.db.commit()
        user_ = self.user_model(user)
        user_['auth_state'] = await user.get_auth_state()
        self.write(json.dumps(user_))


class UserTokenListAPIHandler(APIHandler):
    """API endpoint for listing/creating tokens"""

    # defer check_xsrf_cookie so we can accept auth
    # in the `auth` request field, which shouldn't require xsrf cookies
    _skip_post_check_xsrf = True

    def check_xsrf_cookie(self):
        if self.request.method == 'POST' and self._skip_post_check_xsrf:
            return
        return super().check_xsrf_cookie()

    @needs_scope('read:tokens')
    def get(self, user_name):
        """Get tokens for a given user"""
        user = self.find_user(user_name)
        if not user:
            raise web.HTTPError(404, f"No such user: {user_name}")

        now = utcnow(with_tz=False)
        api_tokens = []

        def sort_key(token):
            return token.last_activity or token.created

        for token in sorted(user.api_tokens, key=sort_key):
            if token.expires_at and token.expires_at < now:
                # exclude expired tokens
                self.db.delete(token)
                self.db.commit()
                continue
            api_tokens.append(self.token_model(token))

        self.write(json.dumps({'api_tokens': api_tokens}))

    async def post(self, user_name):
        body = self.get_json_body() or {}
        if not isinstance(body, dict):
            raise web.HTTPError(400, "Body must be a JSON dict or empty")

        requester = self.current_user
        if requester is None:
            # defer to Authenticator for identifying the user
            # can be username+password or an upstream auth token
            try:
                name = await self.authenticate(body.get('auth'))
                if isinstance(name, dict):
                    # not a simple string so it has to be a dict
                    name = name.get('name')
                # don't check xsrf if we've authenticated via the request body
            except web.HTTPError as e:
                # turn any authentication error into 403
                raise web.HTTPError(403)
            except Exception as e:
                # suppress and log error here in case Authenticator
                # isn't prepared to handle auth via this data
                self.log.error(
                    "Error authenticating request for %s: %s", self.request.uri, e
                )
                raise web.HTTPError(403)
            if name is None:
                raise web.HTTPError(403)
            requester = self.find_user(name)
        else:
            # perform delayed xsrf check
            # if we aren't authenticating via the request body
            self._skip_post_check_xsrf = False
            self.check_xsrf_cookie()
        if requester is None:
            # couldn't identify requester
            raise web.HTTPError(403)
        self._jupyterhub_user = requester
        self._resolve_roles_and_scopes()
        user = self.find_user(user_name)
        kind = 'user' if isinstance(requester, User) else 'service'
        scope_filter = self.get_scope_filter('tokens')
        if user is None or not scope_filter(user, kind):
            raise web.HTTPError(
                403,
                f"{kind.title()} {user_name} not found or no permissions to generate tokens",
            )

        note = body.get('note')
        if not note:
            note = "Requested via api"
            if requester is not user:
                note += f" by {kind} {requester.name}"

        token_roles = body.get("roles")
        token_scopes = body.get("scopes")

        # check type of permissions
        for key in ("roles", "scopes"):
            value = body.get(key)
            if value is None:
                continue
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise web.HTTPError(
                    400, f"token {key} must be null or a list of strings, not {value!r}"
                )

        expires_in = body.get('expires_in', None)
        if not (expires_in is None or isinstance(expires_in, int)):
            raise web.HTTPError(
                400,
                f"token expires_in must be null or integer, not {expires_in!r}",
            )
        expires_in_max = self.settings["token_expires_in_max_seconds"]
        if expires_in_max:
            # validate expires_in against limit
            if expires_in is None:
                # expiration unspecified, use max value
                # (default before max limit was introduced was 'never', this is closest equivalent)
                expires_in = expires_in_max
            elif expires_in > expires_in_max:
                raise web.HTTPError(
                    400,
                    f"token expires_in: {expires_in} must not exceed {expires_in_max}",
                )

        try:
            api_token = user.new_api_token(
                note=note,
                expires_in=expires_in,
                roles=token_roles,
                scopes=token_scopes,
            )
        except (ValueError, KeyError) as e:
            raise web.HTTPError(400, str(e))
        if requester is not user:
            self.log.info(
                "%s %s requested API token for %s",
                kind.title(),
                requester.name,
                user.name,
            )
        else:
            user_kind = 'user' if isinstance(user, User) else 'service'
            self.log.info("%s %s requested new API token", user_kind.title(), user.name)
        # retrieve the model
        orm_token = orm.APIToken.find(self.db, api_token)
        if orm_token is None:
            self.log.error(
                "Failed to find token after creating it: %r. Maybe it expired already?",
                body,
            )
            raise web.HTTPError(500, "Failed to create token")
        token_model = self.token_model(orm_token)
        token_model['token'] = api_token
        self.write(json.dumps(token_model))
        self.set_status(201)


class UserTokenAPIHandler(APIHandler):
    """API endpoint for retrieving/deleting individual tokens"""

    def find_token_by_id(self, user, token_id):
        """Find a token object by token-id key

        Raises 404 if not found for any reason
        (e.g. wrong owner, invalid key format, etc.)
        """
        not_found = f"No such token {token_id} for user {user.name}"
        prefix, id_ = token_id[:1], token_id[1:]
        if prefix != 'a':
            raise web.HTTPError(404, not_found)
        try:
            id_ = int(id_)
        except ValueError:
            raise web.HTTPError(404, not_found)

        orm_token = self.db.query(orm.APIToken).filter_by(id=id_).first()
        if orm_token is None or orm_token.user is not user.orm_user:
            raise web.HTTPError(404, not_found)
        return orm_token

    @needs_scope('read:tokens')
    def get(self, user_name, token_id):
        """"""
        user = self.find_user(user_name)
        if not user:
            raise web.HTTPError(404, f"No such user: {user_name}")
        token = self.find_token_by_id(user, token_id)
        self.write(json.dumps(self.token_model(token)))

    @needs_scope('tokens')
    def delete(self, user_name, token_id):
        """Delete a token"""
        user = self.find_user(user_name)
        if not user:
            raise web.HTTPError(404, f"No such user: {user_name}")
        token = self.find_token_by_id(user, token_id)
        # deleting an oauth token deletes *all* oauth tokens for that client
        client_id = token.client_id
        if token.client_id != "jupyterhub":
            tokens = [
                token for token in user.api_tokens if token.client_id == client_id
            ]
            self.log.info(
                f"Deleting {len(tokens)} tokens for {user_name} issued by {token.client_id}"
            )
        else:
            self.log.info(f"Deleting token {token_id} for {user_name}")
            tokens = [token]
        for token in tokens:
            self.db.delete(token)
        self.db.commit()
        self.set_header('Content-Type', 'text/plain')
        self.set_status(204)


class UserServerAPIHandler(APIHandler):
    """Start and stop single-user servers"""

    @needs_scope('servers')
    async def post(self, user_name, server_name=''):
        user = self.find_user(user_name)
        if user is None:
            # this can be reached if a token has `servers`
            # permission on *all* users
            raise web.HTTPError(404)

        if server_name:
            if not self.allow_named_servers:
                raise web.HTTPError(400, "Named servers are not enabled.")

            named_server_limit_per_user = (
                await self.get_current_user_named_server_limit()
            )

            if named_server_limit_per_user > 0 and server_name not in user.orm_spawners:
                named_spawners = list(user.all_spawners(include_default=False))
                if named_server_limit_per_user <= len(named_spawners):
                    raise web.HTTPError(
                        400,
                        f"User {user_name} already has the maximum of {named_server_limit_per_user} named servers."
                        "  One must be deleted before a new server can be created",
                    )
        spawner = user.get_spawner(server_name, replace_failed=True)
        pending = spawner.pending
        if pending == 'spawn':
            self.set_header('Content-Type', 'text/plain')
            self.set_status(202)
            return
        elif pending:
            raise web.HTTPError(400, f"{spawner._log_name} is pending {pending}")

        if spawner.ready:
            # include notify, so that a server that died is noticed immediately
            # set _spawn_pending flag to prevent races while we wait
            spawner._spawn_pending = True
            try:
                state = await spawner.poll_and_notify()
            finally:
                spawner._spawn_pending = False
            if state is None:
                raise web.HTTPError(400, f"{spawner._log_name} is already running")

        options = self.get_json_body()
        await self.spawn_single_user(user, server_name, options=options)
        status = 202 if spawner.pending == 'spawn' else 201
        self.set_header('Content-Type', 'text/plain')
        self.set_status(status)

    @needs_scope('delete:servers')
    async def delete(self, user_name, server_name=''):
        user = self.find_user(user_name)
        options = self.get_json_body()
        remove = (options or {}).get('remove', False)

        async def _remove_spawner(f=None):
            """Remove the spawner object

            only called after it stops successfully
            """
            if f:
                # await f, stop on error,
                # leaving resources in the db in case of failure to stop
                await f
            self.log.info("Deleting spawner %s", spawner._log_name)
            await maybe_future(user._delete_spawner(spawner))

            self.db.delete(spawner.orm_spawner)
            user.spawners.pop(server_name, None)
            self.db.commit()

        if server_name:
            if not self.allow_named_servers:
                raise web.HTTPError(400, "Named servers are not enabled.")
            if server_name not in user.orm_spawners:
                raise web.HTTPError(
                    404, f"{user_name} has no server named '{server_name}'"
                )
        elif remove:
            raise web.HTTPError(400, "Cannot delete the default server")

        spawner = user.spawners[server_name]
        if spawner.pending == 'stop':
            self.log.debug("%s already stopping", spawner._log_name)
            self.set_header('Content-Type', 'text/plain')
            self.set_status(202)
            if remove:
                # schedule remove when stop completes
                asyncio.ensure_future(_remove_spawner(spawner._stop_future))
            return

        stop_future = None
        if spawner.pending:
            # we are interrupting a pending start
            # hopefully nothing gets leftover
            self.log.warning(
                f"Interrupting spawner {spawner._log_name}, pending {spawner.pending}"
            )
            spawn_future = spawner._spawn_future
            if spawn_future:
                spawn_future.cancel()
            # Give cancel a chance to resolve?
            # not sure what we would wait for here,
            await asyncio.sleep(1)
            stop_future = await self.stop_single_user(user, server_name)

        elif spawner.ready:
            # include notify, so that a server that died is noticed immediately
            status = await spawner.poll_and_notify()
            if status is None:
                stop_future = await self.stop_single_user(user, server_name)

        if remove:
            if stop_future:
                # schedule remove when stop completes
                asyncio.ensure_future(_remove_spawner(spawner._stop_future))
            else:
                await _remove_spawner()

        status = 202 if spawner._stop_pending else 204
        self.set_header('Content-Type', 'text/plain')
        self.set_status(status)


class UserAdminAccessAPIHandler(APIHandler):
    """Grant admins access to single-user servers

    This handler sets the necessary cookie for an admin to login to a single-user server.
    """

    @needs_scope('servers')
    def post(self, user_name):
        self.log.warning(
            "Deprecated in JupyterHub 0.8."
            " Admin access API is not needed now that we use OAuth."
        )
        current = self.current_user
        self.log.warning(
            "Admin user %s has requested access to %s's server", current.name, user_name
        )
        if not self.settings.get('admin_access', False):
            raise web.HTTPError(403, "admin access to user servers disabled")
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(404)


class SpawnProgressAPIHandler(APIHandler):
    """EventStream handler for pending spawns"""

    keepalive_interval = 8

    def get_content_type(self):
        return 'text/event-stream'

    async def send_event(self, event):
        try:
            self.write(f'data: {json.dumps(event)}\n\n')
            await self.flush()
        except StreamClosedError:
            self.log.warning("Stream closed while handling %s", self.request.uri)
            # raise Finish to halt the handler
            raise web.Finish()

    def initialize(self):
        super().initialize()
        self._finish_future = asyncio.Future()

    def on_finish(self):
        self._finish_future.set_result(None)

    async def keepalive(self):
        """Write empty lines periodically

        to avoid being closed by intermediate proxies
        when there's a large gap between events.
        """
        while not self._finish_future.done():
            try:
                self.write("\n\n")
                await self.flush()
            except (StreamClosedError, RuntimeError):
                return

            await asyncio.wait([self._finish_future], timeout=self.keepalive_interval)

    @needs_scope('read:servers')
    async def get(self, user_name, server_name=''):
        self.set_header('Cache-Control', 'no-cache')
        if server_name is None:
            server_name = ''
        user = self.find_user(user_name)
        if user is None:
            # no such user
            raise web.HTTPError(404)
        if server_name not in user.spawners:
            # user has no such server
            raise web.HTTPError(404)
        spawner = user.spawners[server_name]

        # start sending keepalive to avoid proxies closing the connection
        asyncio.ensure_future(self.keepalive())
        # cases:
        # - spawner already started and ready
        # - spawner not running at all
        # - spawner failed
        # - spawner pending start (what we expect)
        failed_event = {'progress': 100, 'failed': True, 'message': "Spawn failed"}

        async def get_ready_event():
            url = url_path_join(user.url, url_escape_path(server_name), '/')
            ready_event = {
                'progress': 100,
                'ready': True,
                'message': f"Server ready at {url}",
                'html_message': f'Server ready at <a href="{url}">{url}</a>',
                'url': url,
            }
            original_ready_event = ready_event.copy()
            if spawner.progress_ready_hook:
                try:
                    ready_event = spawner.progress_ready_hook(spawner, ready_event)
                    if inspect.isawaitable(ready_event):
                        ready_event = await ready_event
                except Exception as e:
                    self.log.exception(f"Error in ready_event hook: {e}")
                    ready_event = original_ready_event
            return ready_event

        if spawner.ready:
            # spawner already ready. Trigger progress-completion immediately
            self.log.info("Server %s is already started", spawner._log_name)
            ready_event = await get_ready_event()
            await self.send_event(ready_event)
            return

        spawn_future = spawner._spawn_future

        if not spawner._spawn_pending:
            # not pending, no progress to fetch
            # check if spawner has just failed
            f = spawn_future
            if f and f.cancelled():
                failed_event['message'] = "Spawn cancelled"
            elif f and f.done() and f.exception():
                exc = f.exception()
                message = getattr(exc, "jupyterhub_message", str(exc))
                failed_event['message'] = f"Spawn failed: {message}"
                html_message = getattr(exc, "jupyterhub_html_message", "")
                if html_message:
                    failed_event['html_message'] = html_message
                await self.send_event(failed_event)
                return
            else:
                raise web.HTTPError(400, "%s is not starting...", spawner._log_name)

        # retrieve progress events from the Spawner
        async with aclosing(
            iterate_until(spawn_future, spawner._generate_progress())
        ) as events:
            try:
                async for event in events:
                    # don't allow events to sneakily set the 'ready' flag
                    if 'ready' in event:
                        event.pop('ready', None)
                    await self.send_event(event)
            except asyncio.CancelledError:
                pass

        # progress finished, wait for spawn to actually resolve,
        # in case progress finished early
        # (ignore errors, which will be logged elsewhere)
        await asyncio.wait([spawn_future])

        # progress and spawn finished, check if spawn succeeded
        if spawner.ready:
            # spawner is ready, signal completion and redirect
            self.log.info("Server %s is ready", spawner._log_name)
            ready_event = await get_ready_event()
            await self.send_event(ready_event)
        else:
            # what happened? Maybe spawn failed?
            f = spawn_future
            if f and f.cancelled():
                failed_event['message'] = "Spawn cancelled"
            elif f and f.done() and f.exception():
                exc = f.exception()
                message = getattr(exc, "jupyterhub_message", str(exc))
                failed_event['message'] = f"Spawn failed: {message}"
                html_message = getattr(exc, "jupyterhub_html_message", "")
                if html_message:
                    failed_event['html_message'] = html_message
            else:
                self.log.warning(
                    "Server %s didn't start for unknown reason", spawner._log_name
                )
            await self.send_event(failed_event)


def _parse_timestamp(timestamp):
    """Parse and return a utc timestamp

    - raise HTTPError(400) on parse error
    - handle and strip tz info for internal consistency
      (we use naive utc timestamps everywhere)
    """
    try:
        dt = parse_date(timestamp)
    except Exception:
        raise web.HTTPError(400, "Not a valid timestamp: %r", timestamp)
    if dt.tzinfo:
        # strip timezone info to naive UTC datetime
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    now = utcnow(with_tz=False)
    if (dt - now) > timedelta(minutes=59):
        raise web.HTTPError(
            400,
            f"Rejecting activity from more than an hour in the future: {isoformat(dt)}",
        )
    return dt


class ActivityAPIHandler(APIHandler):
    def _validate_servers(self, user, servers):
        """Validate servers dict argument

        - types are correct
        - each server exists
        - last_activity fields are parsed into datetime objects
        """
        msg = "servers must be a dict of the form {server_name: {last_activity: timestamp}}"
        if not isinstance(servers, dict):
            raise web.HTTPError(400, msg)

        spawners = user.orm_spawners
        for server_name, server_info in servers.items():
            if server_name not in spawners:
                raise web.HTTPError(
                    400,
                    f"No such server '{server_name}' for user {user.name}",
                )
            # check that each per-server field is a dict
            if not isinstance(server_info, dict):
                raise web.HTTPError(400, msg)
            # check that last_activity is defined for each per-server dict
            if 'last_activity' not in server_info:
                raise web.HTTPError(400, msg)
            # parse last_activity timestamps
            # _parse_timestamp above is responsible for raising errors
            server_info['last_activity'] = _parse_timestamp(
                server_info['last_activity']
            )
        return servers

    @needs_scope('users:activity')
    def post(self, user_name):
        user = self.find_user(user_name)
        if user is None:
            # no such user
            raise web.HTTPError(404, "No such user: %r", user_name)

        body = self.get_json_body()
        if not isinstance(body, dict):
            raise web.HTTPError(400, "body must be a json dict")

        last_activity_timestamp = body.get('last_activity')
        servers = body.get('servers')
        if not last_activity_timestamp and not servers:
            raise web.HTTPError(
                400, "body must contain at least one of `last_activity` or `servers`"
            )

        if servers:
            # validate server args
            servers = self._validate_servers(user, servers)
            # at this point we know that the servers dict
            # is valid and contains only servers that exist
            # and last_activity is defined and a valid datetime object

        # update user.last_activity if specified
        if last_activity_timestamp:
            last_activity = _parse_timestamp(last_activity_timestamp)
            if (not user.last_activity) or last_activity > user.last_activity:
                self.log.debug(
                    "Activity for user %s: %s", user.name, isoformat(last_activity)
                )
                user.last_activity = last_activity
            else:
                self.log.debug(
                    "Not updating activity for %s: %s < %s",
                    user,
                    isoformat(last_activity),
                    isoformat(user.last_activity),
                )

        if servers:
            for server_name, server_info in servers.items():
                last_activity = server_info['last_activity']
                spawner = user.orm_spawners[server_name]

                if (not spawner.last_activity) or last_activity > spawner.last_activity:
                    self.log.debug(
                        "Activity on server %s/%s: %s",
                        user.name,
                        server_name,
                        isoformat(last_activity),
                    )
                    spawner.last_activity = last_activity
                else:
                    self.log.debug(
                        "Not updating server activity on %s/%s: %s < %s",
                        user.name,
                        server_name,
                        isoformat(last_activity),
                        isoformat(user.last_activity),
                    )

        self.db.commit()
    
class SetupStudentHomeAPIHandler(APIHandler):
    """API handler for setting up student home directories for a specific course"""
    
    # def generate_random_string(length=16):
    #     return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    @staticmethod
    def generate_random_string(length=16):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    async def post(self):
        try:
            # Load JSON from raw request body
            raw_data = self.request.body
            try:
                json_data = json.loads(raw_data)
            except json.JSONDecodeError:
                self.set_status(400)
                self.finish(json.dumps({
                    "status": False,
                    "message": "Invalid JSON format"
                }))
                return

            course_name = json_data.get("course_name")

            if not course_name:
                self.set_status(400)
                self.finish(json.dumps({
                    "status": False,
                    "message": "course_name is required"
                }))
                return

            course_user = f"grader-{course_name}"
            cwd_path = f"/home/{course_user}/{course_name}"
            # config_file = "/etc/jupyterhub/jupyterhub_config.py"  # Change if different
            config_file = "/srv/nbgrader/jupyterhub/jupyterhub_config.py"
            folder_path = f"/home/{course_user}"

            os.makedirs(cwd_path, exist_ok=True)
            
            result_useradd = subprocess.run(
                ["sudo", "useradd", course_user],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result_useradd.returncode != 0:
                return self.finish(json.dumps({
                    # return jsonify({
                    "Status": False,
                    "message": f"useradd failed: {result_useradd.stderr.strip()}"
                }))

            result_chmod = subprocess.run(
                ["chmod", "-R", "775", folder_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result_chmod.returncode != 0:
                # return jsonify({
                return self.finish(json.dumps({
                    "Status": False,
                    "message": f"chmod failed: {result_chmod.stderr.strip()}"
                }))

            # Step 3: Change ownership
            result_chown = subprocess.run(
                ["sudo", "chown", f"{course_user}:{course_user}", folder_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result_chown.returncode != 0:
                # return jsonify({
                return self.finish(json.dumps({
                    "Status": False,
                    "message": f"chown failed: {result_chown.stderr.strip()}"
                }))

            with open(config_file, "r") as f:
                lines = f.readlines()

            # Check if course already exists
            if any(course_user in line for line in lines):
                self.set_status(409)
                self.finish(json.dumps({
                    "status": False,
                    "message": f"Course '{course_name}' already exists."
                }))
                return

            # 1. Add to allowed_users
            for i, line in enumerate(lines):
                if line.strip().startswith("c.Authenticator.allowed_users") and "[" in line:
                    start = i
                    while not lines[i].strip().endswith("]"):
                        i += 1
                    end = i
                    user_block = "".join(lines[start:end + 1])
                    if f"'{course_user}'" not in user_block:
                        lines.insert(end, f"    '{course_user}',\n")
                    break

            # 2. Add to load_groups
            for i, line in enumerate(lines):
                if line.strip().startswith("c.JupyterHub.load_groups") and "{" in line:
                    start = i
                    while not lines[i].strip().startswith("}"):
                        i += 1
                    insert_index = i
                    lines.insert(insert_index,
                        f"    'formgrade-{course_name}': [\n"
                        f"        '{course_user}',\n"
                        f"    ],\n"
                        f"    'nbgrader-{course_name}': [\n"
                        f"        'student1',\n"
                        f"    ],\n"
                    )
                    break

            # 3. Add course_name to roles loop list
            # for i, line in enumerate(lines):
            #     if "for course in [" in line.replace(" ", ""):
            #         line = line.strip()
            #         end_idx = line.find("]")
            #         if end_idx != -1:
            #             existing_courses = line[line.find("[")+1:line.find("]")]
            #             course_list = [c.strip().strip("'") for c in existing_courses.split(",") if c.strip()]
            #             if course_name not in course_list:
            #                 course_list.append(course_name)
            #                 updated_line = "for course in [" + ", ".join(f"'{c}'" for c in course_list) + "]:\n"
            #                 lines[i] = updated_line
            #         break
            
            for i, line in enumerate(lines):
                if line.strip().startswith("for course in ["):
                    # Extract course names from the list
                    start_idx = line.find("[")
                    end_idx = line.find("]")
                    if start_idx != -1 and end_idx != -1:
                        existing_courses = line[start_idx+1:end_idx]
                        course_list = [c.strip().strip("'") for c in existing_courses.split(",") if c.strip()]
                        if course_name not in course_list:
                            course_list.append(course_name)
                            updated_line = "for course in [" + ", ".join(f"'{c}'" for c in course_list) + "]:\n"
                            lines[i] = updated_line
                    break

            # 4. Add service block
            for i, line in enumerate(lines):
                if line.strip().startswith("c.JupyterHub.services = ["):
                    insert_index = i + 1
                    used_ports = []
                    for l in lines:
                        if "'url':" in l and "127.0.0.1" in l:
                            try:
                                port = int(l.split(":")[-1].strip().strip("',"))
                                used_ports.append(port)
                            except:
                                continue
                    next_port = max(used_ports + [9996]) + 1
                    random_token = self.generate_random_string()
                    service_str = (
                        f"    {{\n"
                        f"        'name': '{course_name}',\n"
                        f"        'url': 'http://127.0.0.1:{next_port}',\n"
                        f"        'command': [\n"
                        f"            'jupyterhub-singleuser',\n"
                        f"            '--debug',\n"
                        f"        ],\n"
                        f"        'user': 'grader-{course_name}',\n"
                        f"        'cwd': '/home/grader-{course_name}',\n"
                        f"        'environment': {{\n"
                        f"            'JUPYTERHUB_DEFAULT_URL': '/lab'\n"
                        f"        }},\n"
                        f"        'api_token': '{random_token}',\n"
                        f"    }},\n\n"
                    )
                    lines.insert(insert_index, service_str)
                    break

            # Save updated config
            with open(config_file, "w") as f:
                f.writelines(lines)

            # 5. Create nbgrader_config.py
            jupyter_config_dir = f"/home/{course_user}/.jupyter"
            os.makedirs(jupyter_config_dir, exist_ok=True)
            nbgrader_config_path = os.path.join(jupyter_config_dir, "nbgrader_config.py")
            with open(nbgrader_config_path, "w") as config_file_out:
                config_file_out.write("c = get_config()\n")
                config_file_out.write(f"c.CourseDirectory.root = '{cwd_path}'\n")
                config_file_out.write(f"c.CourseDirectory.course_id = '{course_name}'\n")

            # Set permissions (optional, requires subprocess)
            # subprocess.run(["chown", "-R", f"{course_user}:{course_user}", jupyter_config_dir], check=True)

            self.set_status(200)
            self.finish(json.dumps({
                "status": True,
                "message": f"Course '{course_name}' setup completed."
            }))
        except Exception as e:
            self.set_status(500)
            self.set_header("Content-Type", "application/json")
            self.finish(json.dumps({
                "status": False,
                "message": str(e)
            }))
            
# class CreateHomeFolder(APIHandler):
#     async def post(self):
#         try:
#             rollno = self.request.args.get("rollno")
#             folder_path = f"/home/{rollno}"
#             if not os.path.exists(folder_path):
#                 command = [
#                     "useradd", "-m", rollno,
#                     "&&", "chmod", "-R", "775", folder_path,
#                     "&&", "chown", f"{rollno}:{rollno}", folder_path
#                 ]
#                 result = subprocess.run(
#                     " ".join(command),
#                     shell=True,
#                     stdout=subprocess.PIPE,
#                     stderr=subprocess.PIPE,
#                     text=True
#                 )
#                 if result.returncode == 0:
#                     return jsonify({
#                         "Status": True,
#                         "message": "User folder creation successful",
#                     }), 200
#                 else:
#                     return jsonify({
#                         "Status": False,
#                         "message": f"Error: {result.stderr}",
#                     }), 500
#             else:
#                 return jsonify({
#                     "Status": False,
#                     "message": "Folder already exists",
#                 }), 400
#         except Exception as e:
#             return jsonify({
#                 "Status": False,
#                 "message": f"An error occurred: {str(e)}",
#             }), 500
# class CreateHomeFolder(APIHandler):
#     async def post(self):
#         try:
#             rollno = self.get_argument("rollno")
#             folder_path = f"/home/{rollno}"
#             if not os.path.exists(folder_path):
#                 command = f"useradd -m {rollno} && chmod -R 775 {folder_path} && chown {rollno}:{rollno} {folder_path}"
#                 result = subprocess.run(
#                     command,
#                     shell=True,
#                     stdout=subprocess.PIPE,
#                     stderr=subprocess.PIPE,
#                     text=True
#                 )
#                 if result.returncode == 0:
#                     self.set_status(200)
#                     self.finish(json.dumps({
#                         "Status": True,
#                         "message": "User folder creation successful"
#                     }))
#                 else:
#                     self.set_status(500)
#                     self.finish(json.dumps({
#                         "Status": False,
#                         "message": f"Error: {result.stderr}"
#                     }))
#             else:
#                 self.set_status(400)
#                 self.finish(json.dumps({
#                     "Status": False,
#                     "message": "Folder already exists"
#                 }))
#         except Exception as e:
#             self.set_status(500)
#             self.finish(json.dumps({
#                 "Status": False,
#                 "message": f"An error occurred: {str(e)}"
#             }))

class CreateHomeFolder(APIHandler):
    async def post(self):
        try:
            rollno = self.get_argument("rollno")
            folder_path = f"/home/{rollno}"

            if os.path.exists(folder_path):
                self.set_status(400)
                return self.finish(json.dumps({
                    "Status": False,
                    "message": "Folder already exists"
                }))
            # result_useradd = subprocess.run(
            #     ["useradd", "-m", rollno],
            #     stdout=subprocess.PIPE,
            #     stderr=subprocess.PIPE,
            #     text=True
            # )

            # if result_useradd.returncode != 0:
            #     self.set_status(500)
            #     return self.finish(json.dumps({
            #         "Status": False,
            #         "message": f"useradd failed: {result_useradd.stderr.strip()}"
            #     }))

            # All successful
        #     self.set_status(200)
        #     return self.finish(json.dumps({
        #         "Status": True,
        #         "message": "User and home folder created successfully"
        #     }))

        # except Exception as e:
        #     self.set_status(500)
        #     return self.finish(json.dumps({
        #         "Status": False,
        #         "message": f"An error occurred: {e}"
        #     }))

            # Create folder using mkdir -p
            result = subprocess.run(
                ["sudo", "mkdir", "-p", folder_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            result_useradd = subprocess.run(
                ["sudo", "useradd", rollno],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result_useradd.returncode != 0:
                self.set_status(500)
                return self.finish(json.dumps({
                    "Status": False,
                    "message": f"useradd failed: {result_useradd.stderr.strip()}"
                }))
                
            # # Step 2: Change permissions
            result_chmod = subprocess.run(
                ["chmod", "-R", "775", folder_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result_chmod.returncode != 0:
                self.set_status(500)
                return self.finish(json.dumps({
                    "Status": False,
                    "message": f"chmod failed: {result_chmod.stderr.strip()}"
                }))

            # Step 3: Change ownership
            result_chown = subprocess.run(
                ["sudo", "chown", f"{rollno}:{rollno}", folder_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result_chown.returncode != 0:
                self.set_status(500)
                return self.finish(json.dumps({
                    "Status": False,
                    "message": f"chown failed: {result_chown.stderr.strip()}"
                }))

            # subprocess.run(
            #     ["sudo", "useradd", rollno],
            #     stdout=subprocess.PIPE,
            #     stderr=subprocess.PIPE,
            #     text=True
            # )
            # subprocess.run(
            #     ["sudo", "yes", "${rollno}503", "|", "passwd", "${rollno}"],
            #     stdout=subprocess.PIPE,
            #     stderr=subprocess.PIPE,
            #     text=True
            # )

            if result.returncode == 0:
                self.set_status(200)
                self.finish(json.dumps({
                    "Status": True,
                    "message": "Folder created successfully"
                }))
            else:
                self.set_status(500)
                self.finish(json.dumps({
                    "Status": False,
                    "message": f"Error: {result.stderr}"
                }))

        except Exception as e:
            self.set_status(500)
            self.finish(json.dumps({
                "Status": False,
                "message": f"An error occurred: {str(e)}"
            }))

class AssignmentsPage(APIHandler):

    # ======================================================
    #  GET COURSE TYPE (MySQL)  – SYNC HELPER
    # ======================================================
    def get_course_type_sync(self, course):
        import mysql.connector
        self.log.debug(f"[MYSQL] Checking course type for '{course}'")

        try:
            conn = mysql.connector.connect(
                host="172.168.15.216",
                user="assessment",
                password="Tele123$",
                database="tantrik_docker"
            )
            cursor = conn.cursor()

            cursor.execute("SELECT type FROM course WHERE name = %s", (course,))
            row = cursor.fetchone()

            cursor.close()
            conn.close()

            if row and row[0]:
                self.log.debug(f"[MYSQL] Course '{course}' → type={row[0]}")
                return row[0].lower()

            self.log.warning(f"[MYSQL] No course type for '{course}', defaulting to strict")
            return "strict"

        except Exception as e:
            self.log.error(f"[MYSQL ERROR] get_course_type: {e}", exc_info=True)
            return "strict"

    # ======================================================
    #  UTIL: Convert UTC → IST
    # ======================================================
    def to_ist(self, utc_dt_str):
        if not utc_dt_str:
            return None

        try:
            self.log.debug(f"[TIME] Converting timestamp UTC→IST: {utc_dt_str}")

            ist = pytz.timezone("Asia/Kolkata")

            try:
                dt_utc = datetime.strptime(utc_dt_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                dt_utc = datetime.strptime(utc_dt_str, "%Y-%m-%d %H:%M:%S")

            dt_utc = pytz.utc.localize(dt_utc)
            dt_ist = dt_utc.astimezone(ist)

            formatted = dt_ist.strftime("%Y-%m-%d %I:%M %p")
            return formatted

        except Exception as e:
            self.log.error(f"[TIME ERROR] Failed converting UTC→IST: {e}", exc_info=True)
            return utc_dt_str

    # ======================================================
    #  GET LATEST SUBMISSION TIME – SYNC
    # ======================================================
    def get_latest_submission_time_sync(self, db_path, assignment_name, student_id):
        self.log.debug(f"[SQLITE] Fetching latest submission for {student_id}:{assignment_name}")

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            query = """
                SELECT s.timestamp
                FROM submitted_assignment s
                JOIN assignment a ON a.id = s.assignment_id
                WHERE a.name = ? AND s.student_id = ?
                ORDER BY s.timestamp DESC
                LIMIT 1
            """

            cursor.execute(query, (assignment_name, student_id))
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                raw = row[0]
                ist = self.to_ist(raw)
                self.log.debug(f"[SQLITE] Latest submission → {raw} (IST {ist})")
                return raw, ist

            self.log.debug(f"[SQLITE] No submissions found for {assignment_name}")
            return None, None

        except Exception as e:
            self.log.error(f"[ERROR] get_latest_submission_time: {e}", exc_info=True)
            return None, None

    # ======================================================
    #  SUBMIT LOGIC – SYNC
    # ======================================================
    def submit_assignment_sync(self, course_name, assignment_name, student_id):
        self.log.debug(f"[NBGRADER] Submitting assignment '{assignment_name}' for '{student_id}'")

        try:
            student_home = os.path.expanduser(f"~{student_id}")
            assignment_path = os.path.join(student_home, course_name, assignment_name)

            if not os.path.exists(assignment_path):
                self.log.warning(f"[SUBMIT] Assignment folder missing: {assignment_path}")
                return {"error": True, "message": "Assignment folder not found"}

            cmd = [
                "sudo", "-E", "-u", student_id,
                "/usr/local/bin/nbgrader", "submit",
                assignment_name, "--course", course_name
            ]

            API_TOKEN = "871fd3d342d74f1dbb4a296dc450b8a8"

            env = os.environ.copy()
            env["JUPYTERHUB_USER"] = student_id
            env["JUPYTERHUB_API_URL"] = "http://127.0.0.1:8081/hub/api"
            env["JUPYTERHUB_API_TOKEN"] = API_TOKEN
            env["HOME"] = student_home
            env["USER"] = student_id
            env["LOGNAME"] = student_id

            result = subprocess.run(
                cmd,
                cwd=student_home,
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.log.debug(f"[SUBMIT SUCCESS] {student_id}:{assignment_name}")
                return {"error": False, "message": "Submission successful"}

            self.log.error(f"[SUBMIT FAILED] {result.stderr}")
            return {"error": True, "message": f"Submission failed: {result.stderr.strip()}"}

        except Exception as e:
            self.log.error(f"[SUBMIT ERROR] {e}", exc_info=True)
            return {"error": True, "message": str(e)}

    # ======================================================
    #  FETCH FEEDBACK – SYNC
    # ======================================================
    def fetch_feedback_sync(self, course_name, assignment_name, student_id):
        self.log.debug(f"[NBGRADER] Fetching feedback for {student_id}:{assignment_name}")

        try:
            student_home = os.path.expanduser(f"~{student_id}")

            cmd = [
                "sudo", "-E", "-u", student_id,
                "/usr/local/bin/nbgrader", "fetch_feedback",
                assignment_name,
                "--course", course_name
            ]

            env = os.environ.copy()
            env["JUPYTERHUB_USER"] = student_id
            env["JUPYTERHUB_API_URL"] = "http://127.0.0.1:8081/hub/api"
            env["JUPYTERHUB_API_TOKEN"] = os.environ.get(
                "JUPYTERHUB_API_TOKEN",
                "871fd3d342d74f1dbb4a296dc450b8a8",
            )
            env["HOME"] = student_home

            result = subprocess.run(
                cmd, cwd=student_home, env=env, capture_output=True, text=True
            )

            if result.returncode == 0:
                self.log.debug(f"[FEEDBACK SUCCESS] {student_id}:{assignment_name}")
                return {"error": False, "message": f"Feedback fetched successfully"}

            self.log.error(f"[FEEDBACK FAILED] {result.stderr}")
            return {"error": True, "message": result.stderr.strip()}

        except Exception as e:
            self.log.error(f"[FEEDBACK ERROR] {e}", exc_info=True)
            return {"error": True, "message": str(e)}

    # ======================================================
    #  FETCH ASSIGNMENT – SYNC
    # ======================================================
    def fetch_assignment_sync(self, course_name, assignment_name, student_id):
        self.log.debug(f"[NBGRADER] Fetching assignment '{assignment_name}' for '{student_id}'")

        try:
            student_home = os.path.expanduser(f"~{student_id}")

            cmd = [
                "sudo", "-E", "-u", student_id,
                "/usr/local/bin/nbgrader", "fetch_assignment",
                assignment_name, "--course", course_name
            ]

            env = os.environ.copy()
            env["JUPYTERHUB_USER"] = student_id
            env["JUPYTERHUB_API_URL"] = "http://127.0.0.1:8081/hub/api"
            env["JUPYTERHUB_API_TOKEN"] = os.environ.get(
                "JUPYTERHUB_API_TOKEN",
                "871fd3d342d74f1dbb4a296dc450b8a8",
            )
            env["HOME"] = student_home

            os.makedirs(student_home, exist_ok=True)

            result = subprocess.run(
                cmd, cwd=student_home, env=env, capture_output=True, text=True
            )

            if result.returncode == 0:
                self.log.debug(f"[FETCH SUCCESS] Assignment fetched")
                return {"error": False, "message": f"✅ Successfully fetched {assignment_name}!"}

            self.log.error(f"[FETCH FAILED] {result.stderr}")
            return {"error": True, "message": result.stderr.strip()}

        except Exception as e:
            self.log.error(f"[FETCH ERROR] {e}", exc_info=True)
            return {"error": True, "message": str(e)}

    # ======================================================
    #  GET GRADE OF STUDENT – SYNC
    # ======================================================
    def get_grade_of_student_sync(self, db_path, assignment_name, student_id):
        self.log.debug(f"[GRADE] Fetching grade for {student_id}:{assignment_name}")

        try:
            with Gradebook(f"sqlite:///{db_path}") as gb:
                submission = gb.find_submission(assignment_name, student_id)

                if not submission:
                    self.log.debug("[GRADE] No grade found")
                    return {"score": None, "max_score": None}

                return {"score": submission.score, "max_score": submission.max_score}

        except Exception as e:
            self.log.warning(f"[WARN] get_grade_of_student: {e}", exc_info=True)
            return {"score": None, "max_score": None}

    # ======================================================
    #  GET SCORES – SYNC
    # ======================================================
    def get_student_scores_sync(self, db_path, student_id):
        self.log.debug(f"[GRADEBOOK] Loading all scores for '{student_id}'")
        scores = {}

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT a.name
                FROM submitted_assignment s
                JOIN assignment a ON a.id = s.assignment_id
                WHERE s.student_id = ?
            """, (student_id,))

            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                assignment_name = r[0]
                grade = self.get_grade_of_student_sync(db_path, assignment_name, student_id)
                scores[assignment_name] = grade

            return scores

        except Exception as e:
            self.log.warning(f"[WARN] get_student_scores: {e}", exc_info=True)
            return scores

    # ======================================================
    #  MAIN GET HANDLER
    # ======================================================
    @web.authenticated
    async def get(self):
        username = self.current_user.name
        action = self.get_argument("action", None)
        selected_course = self.get_argument("course", None)
        assignment_name = self.get_argument("assignment", None)

        self.log.debug(f"[HTTP GET] user={username}, action={action}, course={selected_course}, assignment={assignment_name}")

        # ------------------------ SUBMIT ------------------------
        # if action == "submit" and selected_course and assignment_name:
        #     try:
        #         result = await asyncio.to_thread(
        #             self.submit_assignment_sync, selected_course, assignment_name, username
        #         )
        #         self.finish(result)
        #     except Exception as e:
        #         self.log.error(f"[ERROR] During submission: {e}", exc_info=True)
        #         self.finish({"error": True, "message": str(e)})
        #     return
        
        # ------------------------ SUBMIT ------------------------
        if action == "submit" and selected_course and assignment_name:
            try:
                course = selected_course
                student_home = os.path.expanduser(f"~{username}")
                gradebook_path = f"/home/grader-{course}/{course}/gradebook.db"

                # Load scores
                scores = {}
                if os.path.exists(gradebook_path):
                    scores = await asyncio.to_thread(
                        self.get_student_scores_sync, gradebook_path, username
                    )

                grade_info = scores.get(assignment_name, {})
                score = grade_info.get("score") or 0
                max_score = grade_info.get("max_score") or 0

                percent = (score / max_score * 100) if max_score > 0 else 0

                # --------- CHECK NEXT ASSIGNMENT FETCHED ----------
                outbound_path = f"/usr/local/share/nbgrader/exchange/{course}/outbound"
                raw = [
                    a for a in os.listdir(outbound_path)
                    if os.path.isdir(os.path.join(outbound_path, a))
                ]

                desired_order = ["user", "application", "development", "research"]

                def level(a):
                    parts = a.split("_")
                    return parts[-1].lower() if parts else a.lower()

                sorted_assignments = sorted(
                    raw,
                    key=lambda a: desired_order.index(level(a)) if level(a) in desired_order else 999
                )

                next_assignment_fetched = False

                if assignment_name in sorted_assignments:
                    index = sorted_assignments.index(assignment_name)

                    if index < len(sorted_assignments) - 1:
                        next_assignment = sorted_assignments[index + 1]
                        next_assignment_dir = os.path.join(
                            student_home,
                            course,
                            next_assignment
                        )

                        if os.path.exists(next_assignment_dir):
                            next_assignment_fetched = True

                # --------- FINAL SUBMISSION BLOCK CONDITION ---------

                if (percent >= 50 and next_assignment_fetched) or percent == 100:
                    self.finish({
                        "error": True,
                        "message": "Submission not allowed. You already passed and moved ahead."
                    })
                    return

                # If allowed → proceed
                result = await asyncio.to_thread(
                    self.submit_assignment_sync, selected_course, assignment_name, username
                )
                self.finish(result)

            except Exception as e:
                self.log.error(f"[ERROR] During submission: {e}", exc_info=True)
                self.finish({"error": True, "message": str(e)})

            return


        # ---------------------- FETCH FEEDBACK ----------------------
        if action == "fetch_feedback" and selected_course and assignment_name:
            self.finish(
                await asyncio.to_thread(
                    self.fetch_feedback_sync, selected_course, assignment_name, username
                )
            )
            return

        # ------------------------ FETCH ASSIGNMENT ------------------------
        if action == "fetch" and selected_course and assignment_name:
            course = selected_course
            student_home = os.path.expanduser(f"~{username}")
            course_type = await asyncio.to_thread(self.get_course_type_sync, course)
            self.log.debug(f"[COURSE TYPE] {course} = {course_type}")

            gradebook_path = f"/home/grader-{course}/{course}/gradebook.db"
            outbound_path = f"/usr/local/share/nbgrader/exchange/{course}/outbound"

            scores = {}
            if os.path.exists(gradebook_path):
                scores = await asyncio.to_thread(
                    self.get_student_scores_sync, gradebook_path, username
                )

            # Sorting
            desired_order = ["user", "application", "development", "research"]

            def level(a):
                return a.split("_")[-1].lower()

            folders = [
                a for a in os.listdir(outbound_path)
                if os.path.isdir(os.path.join(outbound_path, a))
            ]

            sorted_assignments = sorted(
                folders,
                key=lambda a: desired_order.index(level(a)) if level(a) in desired_order else 999
            )

            if course_type == "strict":
                if assignment_name in sorted_assignments:
                    index = sorted_assignments.index(assignment_name)

                    if index > 0:
                        previous = sorted_assignments[index - 1]
                        prev_grade = scores.get(previous, {})
                        prev_score = prev_grade.get("score") or 0
                        prev_max = prev_grade.get("max_score") or 0

                        percent = (prev_score / prev_max * 100) if prev_max > 0 else 0

                        if percent < 50:
                            self.finish({
                                "error": True,
                                "message": "❌ You must score more than 50% in the previous assignment."
                            })
                            return

            assignment_dir = os.path.join(student_home, course, assignment_name)

            if os.path.exists(assignment_dir):
                self.finish({"error": False, "already_fetched": True, "message": "Already fetched"})
                return

            # Fetch assignment
            result = await asyncio.to_thread(
                self.fetch_assignment_sync, selected_course, assignment_name, username
            )
            self.finish(result)
            return

        # ------------------------ LIST ASSIGNMENTS ------------------------
        if not selected_course:
            self.finish({"error": True, "message": "No course selected"})
            return

        course = selected_course
        course_type = await asyncio.to_thread(self.get_course_type_sync, course)

        outbound_path = f"/usr/local/share/nbgrader/exchange/{course}/outbound"
        gradebook_path = f"/home/grader-{course}/{course}/gradebook.db"

        assignments = []
        scores = {}

        if os.path.exists(gradebook_path):
            scores = await asyncio.to_thread(
                self.get_student_scores_sync, gradebook_path, username
            )

        desired_order = ["user", "application", "development", "research"]

        if os.path.exists(outbound_path):
            raw = [
                a for a in os.listdir(outbound_path)
                if os.path.isdir(os.path.join(outbound_path, a))
            ]

            def level(a):
                parts = a.split("_")
                return parts[-1].lower() if parts else a.lower()

            sorted_assignments = sorted(
                raw,
                key=lambda a: desired_order.index(level(a)) if level(a) in desired_order else 999
            )
            
            student_home = os.path.expanduser(f"~{username}")
            for index, a in enumerate(sorted_assignments):
                path = os.path.join(outbound_path, a)

                try:
                    notebooks = [nb for nb in os.listdir(path) if nb.endswith(".ipynb")]
                except Exception:
                    notebooks = []

                grade_info = scores.get(a, {})
                score = grade_info.get("score")
                max_score = grade_info.get("max_score")

                if score is None:
                    grade_str = "—"
                else:
                    grade_str = f"{score}/{max_score}"

                raw_ts, ist_ts = await asyncio.to_thread(
                    self.get_latest_submission_time_sync,
                    gradebook_path,
                    a,
                    username,
                )
                
                # ======================================================
                # CHECK NEXT ASSIGNMENT FETCHED (STRICT MODE)
                # ======================================================
                
                next_assignment_fetched = False
                current_assignment_fetched = False
                
                if course_type == "strict":
                    current_assignment = sorted_assignments[index]
                    current_assignment_dir = os.path.join(
                        student_home,
                        course,
                        current_assignment
                    )
                    if os.path.exists(current_assignment_dir):
                        current_assignment_fetched = True

                if course_type == "strict" and index < len(sorted_assignments) - 1:
                    next_assignment = sorted_assignments[index + 1]

                    next_assignment_dir = os.path.join(
                        student_home,
                        course,
                        next_assignment
                    )

                    if os.path.exists(next_assignment_dir):
                        next_assignment_fetched = True


                assignments.append({
                    "name": a,
                    "notebooks": notebooks,
                    "level": level(a).upper(),
                    "status": "Available",
                    "grade": grade_str,
                    "submitted_at": ist_ts or "—",
                    "submitted_at_utc": f"{raw_ts} UTC" if raw_ts else None,
                    "next_assignment_fetched": next_assignment_fetched,
                    "current_assignment_fetched": current_assignment_fetched,
                })

        self.finish({
            "error": False,
            "assignments": assignments,
            "course_type": course_type
        })
        
class PermissionHandler(APIHandler):

    async def post(self):

        data = json.loads(self.request.body)

        students = data.get("students", [])
        course = data.get("course")

        success = []
        failed = []

        for student in students:

            path = f"/home/{student}/{course}"

            try:
                if os.path.exists(path):

                    subprocess.run(
                        ["chmod", "-R", "000", path],
                        check=True
                    )

                    success.append(student)

                else:
                    failed.append({
                        "student": student,
                        "error": "folder not found"
                    })

            except Exception as e:

                failed.append({
                    "student": student,
                    "error": str(e)
                })

        self.finish({
            "success": success,
            "failed": failed
        })


default_handlers = [
    (r"/api/user", SelfAPIHandler),
    (r"/api/createhomefolder", CreateHomeFolder),
    (r"/api/hello/([^/]+)", HelloAPIHandler),
    (r"/api/totalstudents", TotalStudentsAPIHandler),
    (r"/api/activestudents", ActiveStudentsAPIHandler),
    (r"/api/submittedcount", SubmittedCountAPIHandler),
    (r"/api/feedbackfile", FeedbackFileAPIHandler),
    (r"/api/upload", GenerateAssignmentAPIHandler),
    (r"/api/releaseassignment", ReleaseAssignmentAPIHandler),
    (r"/api/unreleaseassignment", UnreleaseAssignmentAPIHandler),
    (r"/api/setup_student_home", SetupStudentHomeAPIHandler),
    (r"/api/autograde", AutogradeAPIHandler),
    (r"/api/re-evaluate", ReEvaluatingAPIHandler),
    (r"/api/users", UserListAPIHandler),
    (r"/api/users/([^/]+)", UserAPIHandler),
    (r"/api/users/([^/]+)/server", UserServerAPIHandler),
    (r"/api/users/([^/]+)/server/progress", SpawnProgressAPIHandler),
    (r"/api/users/([^/]+)/tokens", UserTokenListAPIHandler),
    (r"/api/users/([^/]+)/tokens/([^/]*)", UserTokenAPIHandler),
    (r"/api/users/([^/]+)/servers/([^/]*)", UserServerAPIHandler),
    (r"/api/users/([^/]+)/servers/([^/]*)/progress", SpawnProgressAPIHandler),
    (r"/api/users/([^/]+)/activity", ActivityAPIHandler),
    (r"/api/users/([^/]+)/admin-access", UserAdminAccessAPIHandler),
    (r"/api/assignments", AssignmentsPage),
    (r"/api/permissions", PermissionHandler),

]