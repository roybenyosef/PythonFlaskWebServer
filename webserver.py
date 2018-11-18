import sys
import requests
from flask import Flask, jsonify, request
from pony.orm import *
from pony.orm.serialization import to_dict
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
db = Database()

class Github(db.Entity):
    commitId = Required(str)
    username = Required(str)
    repoName = Required(str)
    repoId = Required(str)

class Jenkins(db.Entity):
    commitId = Required(str)
    artifactChecksum = Required(str)

class Artifactory(db.Entity):
    commitId = Required(str)
    artifactChecksum = Required(str)

class Application(db.Entity):
    artifactoryOk = Required(bool)
    jenkinsOk = Required(bool)
    githubOk = Required(bool)
    rawData = Required(str)

@db_session
def add_github_data(commitData):
    githubData = Github(commitId=commitData['commits'][0]['id'].upper(),\
        username=commitData['commits'][0]['author']['username'],\
        repoId=str(commitData['repository']['id']),\
        repoName=commitData['repository']['name'])

@db_session
def add_jenkins_data(data):
    jenkinsData = Jenkins(commitId=data['gitCommit'].upper(), artifactChecksum=data['artifactChecksum'].upper())


@db_session
def add_artifactory_data(data):
    artifact = data['artifactory']['webhook']['data']['repoPath']['path']
    repo = data['artifactory']['webhook']['data']['repoPath']['repoKey']
    artifactInfo = requests.get('http://http://ec2-18-188-184-139.us-east-2.compute.amazonaws.com:8081/artifactory/ui/artifactproperties?path=' + artifact + '&repoKey=' + repo)
    if artifactInfo.status_code == 200:
        artifactInfoResponse = artifactInfo.json()
        jsonCommitId = "None"
        for item in artifactInfoResponse['artifactProperties']:
            if item['name'] == 'vcs.revision':
                jsonCommitId = item['value'].upper()

        arti = Artifactory(commitId=jsonCommitId, artifactChecksum=data['artifactory']['webhook']['data']['sha1'].upper())

@db_session
def is_valid(checksum):

    artifact_dict = { "Artifactory" : {} }
    artifact = Artifactory.select(lambda a: a.artifactChecksum == checksum).first()
    if (artifact == None):
        app.logger.info('artifact with checksum ' + checksum + ' is None')
    else:
        artifact_dict = to_dict(artifact)

    jenkins_dict = { "Jenkins" : {} }
    jenkins = Jenkins.select(lambda j: j.artifactChecksum == checksum).first()
    if (jenkins == None):
        app.logger.info('jenkins is None for checksum:' + checksum)
    else:
        jenkins_dict = to_dict(jenkins)

    github_dict = { "Github" : {} }
    github = None
    if (artifact != None):
        github = Github.select(lambda g: g.commitId == artifact.commitId).first()
        if (github == None):
            app.logger.info('github is None for commitid:' + artifact.commitId)
        else:
            github_dict = to_dict(github)

    rawData = jsonify(artifact_dict, jenkins_dict, github_dict).get_data(as_text = True)

    application = Application(artifactoryOk = artifact != None, 
                              jenkinsOk = jenkins != None, 
                              githubOk = github != None, 
                              rawData = rawData);
    
    if (artifact != None and github != None and jenkins != None):
        app.logger.info('all validations passed')
        return True
    else:
        app.logger.info('some validations failed')
        return False


db.bind(provider='postgres', user='postgres', password='123Cyber', host='db', database='')
#to work on 127.0.0.1
#db.bind(provider='postgres', user='postgres', password='123Cyber', database='')

db.generate_mapping(create_tables=True)

@app.route('/application/<checksum>')
def hello_world(checksum):
    exists = is_valid(checksum)
    return jsonify(valid=exists)

@app.route('/summary')
def get_summary():
    return get_summary_from_db()


@db_session
def get_summary_from_db():
    app.logger.info('get_summary_from_db 0.1')

    application = Application.select().order_by(Application.id.desc()).first()
    if application == None:
        return jsonify() 
    
    return jsonify(
        appsCount = count(a for a in Application), 
        artifactsCount = count(a for a in Artifactory),
        buildsCount = count(b for b in Jenkins),
        commitsCount = count(c for c in Github),
        summary = ({   
                        "label" : "Github",
                        "ok" : application.githubOk, 
                        "rawData" : application.rawData 
                    },
                    {   
                        "label" : "Jenkins",
                        "ok" : application.jenkinsOk, 
                        "rawData" : application.rawData 
                    },
                    {   
                        "label" : "Artifactory",
                        "ok" : application.artifactoryOk, 
                        "rawData" : application.rawData 
                    }))
                    


@app.route('/ingress/<system>', methods=['POST'])
def post_something(system):
    content = request.json
    app.logger.info("***** ingress from: " + system + " *****")
    app.logger.info(content)

    if system == 'github':
        add_github_data(content)
    elif system == 'jenkins':
        add_jenkins_data(content)
    elif system == 'artifactory':
        add_artifactory_data(content)

    resp = jsonify(content)
    resp.status_code = 201

    return resp

if __name__ == "__main__":
    app.logger.info('running m3l server 0.1')
    app.run(host="0.0.0.0", debug=True)