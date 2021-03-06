from fabric.api import *
import os.path
import pystache

env.roledefs = {
    'app': ['10.29.9.3'],
    'db': ['10.29.9.4']
}

def _put_parsed_file(template_path, destination, data):
    with open(template_path, 'r') as template:
        result = pystache.render(template.read(), data)
    temp_file = "/tmp/" + os.path.basename(template_path)
    with open(temp_file, 'w') as script:
        script.write(result)
    put(temp_file, destination, mode=0755)
    

@roles("db")
def deploy_db():
    _put_parsed_file("vms/install_db.sh.template", "/tmp/install_db.sh", {'hosts': env.roledefs['app']})
    sudo("/tmp/install_db.sh", shell=False)
    
@roles("app")
def init_db():
    run("cd ~/class2go/main && python manage.py syncdb --noinput")
    run("cd ~/class2go/main && python manage.py syncdb --database=celery")
    migrate_db()

@roles("app")
def migrate_db():
    run("cd ~/class2go/main && python manage.py migrate")
    run("cd ~/class2go/main && python manage.py migrate --database=celery")

@roles("app")
def create_tw_institution():
    run("cd ~/class2go/main && python manage.py create_tw_institution")

@roles("app")
def update_site():
    run("cd ~/class2go/main && python manage.py update_site classroom.thoughtworks.com")
    
@roles("app")
def create_super_user():
    run("cd ~/class2go/main && python manage.py createsuperuser")

def _install_chef():
    put("vms/install_chef.sh", "/tmp/install_chef.sh", mode=0755)
    sudo("/tmp/install_chef.sh")

def _prepare_chef_solo(data):
    local("tar czf /tmp/c2g-chef.tgz chef")
    put("/tmp/c2g-chef.tgz", "/tmp/c2g-chef.tgz")
    sudo("rm -rf /tmp/c2g-chef /tmp/chef solo.rb chef.json")
    run("tar xzf /tmp/c2g-chef.tgz -C /tmp")
    put("vms/solo.rb", "/tmp/solo.rb")
    _put_parsed_file("vms/chef.json.template", "/tmp/chef.json", data)

@roles("app")
def deploy_app(user='vagrant', group='admin', 
               admin_email='admin@example.com', smtp_user='', smtp_password='', server_email='noreply@example.com',
               aws_key='', aws_secret='', 
               piazza_key='thoughtworks.com', piazza_secret='',
               db_host=env.roledefs['db'][0],
               files_root_url='http://media.server/media/'):
    _install_chef()
    data = {
        'user' : user,
        'group' : group,
        'admin_email' : admin_email,
        'server_email' : server_email,
        'smtp_user' : smtp_user,
        'smtp_password' : smtp_password,
        'aws_key' : aws_key,
        'aws_secret' : aws_secret,
        'piazza_key' : piazza_key,
        'piazza_secret' : piazza_secret,
        'db_host' : db_host,
        'files_root_url' : files_root_url
        }
    _prepare_chef_solo(data)
    sudo("chef-solo -c /tmp/solo.rb -j /tmp/chef.json")
