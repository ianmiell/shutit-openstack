# Generated by shutit skeleton
import random
import datetime
import logging
import string
import os
import inspect
from shutit_module import ShutItModule

class shutit_openstack(ShutItModule):


	def build(self, shutit):
		vagrant_image = shutit.cfg[self.module_id]['vagrant_image']
		vagrant_provider = shutit.cfg[self.module_id]['vagrant_provider']
		gui = shutit.cfg[self.module_id]['gui']
		memory = shutit.cfg[self.module_id]['memory']
		shutit.build['vagrant_run_dir'] = os.path.dirname(os.path.abspath(inspect.getsourcefile(lambda:0))) + '/vagrant_run'
		shutit.build['module_name'] = 'shutit_openstack_' + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
		shutit.build['this_vagrant_run_dir'] = shutit.build['vagrant_run_dir'] + '/' + shutit.build['module_name']
		shutit.send(' command rm -rf ' + shutit.build['this_vagrant_run_dir'] + ' && command mkdir -p ' + shutit.build['this_vagrant_run_dir'] + ' && command cd ' + shutit.build['this_vagrant_run_dir'])
		shutit.send('command rm -rf ' + shutit.build['this_vagrant_run_dir'] + ' && command mkdir -p ' + shutit.build['this_vagrant_run_dir'] + ' && command cd ' + shutit.build['this_vagrant_run_dir'])
		if shutit.send_and_get_output('vagrant plugin list | grep landrush') == '':
			shutit.send('vagrant plugin install landrush')
		shutit.send('vagrant init ' + vagrant_image)
		shutit.send_file(shutit.build['this_vagrant_run_dir'] + '/Vagrantfile','''Vagrant.configure("2") do |config|
  config.landrush.enabled = true
  config.vm.provider "virtualbox" do |vb|
    vb.gui = ''' + gui + '''
    vb.memory = "''' + memory + '''"
  end

  config.vm.define "openstack1" do |openstack1|
    openstack1.vm.box = ''' + '"' + vagrant_image + '"' + '''
    openstack1.vm.hostname = "openstack1.vagrant.test"
    config.vm.provider :virtualbox do |vb|
      vb.name = "shutit_openstack_1"
    end
  end
end''')

		# machines is a dict of dicts containing information about each machine for you to use.
		machines = {}
		machines.update({'openstack1':{'fqdn':'openstack1.vagrant.test'}})

		try:
			pw = open('secret').read().strip()
		except IOError:
			pw = ''
		if pw == '':
			shutit.log("""You can get round this manual step by creating a 'secret' with your password: 'touch secret && chmod 700 secret'""",level=logging.CRITICAL)
			pw = shutit.get_env_pass()
			import time
			time.sleep(10)

		# Set up the sessions
		shutit_sessions = {}
		for machine in sorted(machines.keys()):
			shutit_sessions.update({machine:shutit.create_session('bash')})
		# Set up and validate landrush
		for machine in sorted(machines.keys()):
			shutit_session = shutit_sessions[machine]
			shutit_session.send('cd ' + shutit.build['this_vagrant_run_dir'])
			# Remove any existing landrush entry.
			shutit_session.send('vagrant landrush rm ' + machines[machine]['fqdn'])
			# Needs to be done serially for stability reasons.
			try:
				shutit_session.multisend('vagrant up --provider ' + shutit.cfg['shutit-library.virtualization.virtualization.virtualization']['virt_method'] + ' ' + machine,{'assword for':pw,'assword:':pw})
			except NameError:
				shutit.multisend('vagrant up ' + machine,{'assword for':pw,'assword:':pw},timeout=99999)
			if shutit.send_and_get_output("vagrant status 2> /dev/null | grep -w ^" + machine + " | awk '{print $2}'") != 'running':
				shutit.pause_point("machine: " + machine + " appears not to have come up cleanly")
			ip = shutit.send_and_get_output('''vagrant landrush ls 2> /dev/null | grep -w ^''' + machines[machine]['fqdn'] + ''' | awk '{print $2}' ''')
			machines.get(machine).update({'ip':ip})
			shutit_session.login(command='vagrant ssh ' + machine)
			shutit_session.login(command='sudo su - ')
			shutit_session.send('sysctl -w net.ipv4.conf.all.route_localnet=1')
			# Correct /etc/hosts
			shutit_session.send(r'''cat <(echo $(ip -4 -o addr show scope global | grep -v 10.0.2.15 | head -1 | awk '{print $4}' | sed 's/\(.*\)\/.*/\1/') $(hostname)) <(cat /etc/hosts | grep -v $(hostname -s)) > /tmp/hosts && mv -f /tmp/hosts /etc/hosts''')
			# Correct any broken ip addresses.
			if shutit.send_and_get_output('''vagrant landrush ls | grep ''' + machine + ''' | grep 10.0.2.15 | wc -l''') != '0':
				shutit_session.log('A 10.0.2.15 landrush ip was detected for machine: ' + machine + ', correcting.',level=logging.WARNING)
				# This beaut gets all the eth0 addresses from the machine and picks the first one that it not 10.0.2.15.
				while True:
					ipaddr = shutit_session.send_and_get_output(r'''ip -4 -o addr show scope global | grep -v 10.0.2.15 | head -1 | awk '{print $4}' | sed 's/\(.*\)\/.*/\1/' ''')
					if ipaddr[0] not in ('1','2','3','4','5','6','7','8','9'):
						time.sleep(10)
					else:
						break
				# Send this on the host (shutit, not shutit_session)
				shutit.send('vagrant landrush set ' + machines[machine]['fqdn'] + ' ' + ipaddr)
			# Check that the landrush entry is there.
			shutit.send('vagrant landrush ls | grep -w ' + machines[machine]['fqdn'])
		# Gather landrush info
		for machine in sorted(machines.keys()):
			ip = shutit.send_and_get_output('''vagrant landrush ls 2> /dev/null | grep -w ^''' + machines[machine]['fqdn'] + ''' | awk '{print $2}' ''')
			machines.get(machine).update({'ip':ip})



		for machine in sorted(machines.keys()):
			shutit_session = shutit_sessions[machine]
			shutit_session.run_script(r'''#!/bin/sh
# See https://raw.githubusercontent.com/ianmiell/vagrant-swapfile/master/vagrant-swapfile.sh
fallocate -l ''' + shutit.cfg[self.module_id]['swapsize'] + r''' /swapfile
ls -lh /swapfile
chown root:root /swapfile
chmod 0600 /swapfile
ls -lh /swapfile
mkswap /swapfile
swapon /swapfile
swapon -s
grep -i --color swap /proc/meminfo
echo "
/swapfile none            swap    sw              0       0" >> /etc/fstab''')
			shutit_session.multisend('adduser person',{'Enter new UNIX password':'person','Retype new UNIX password:':'person','Full Name':'','Phone':'','Room':'','Other':'','Is the information correct':'Y'})

		for machine in sorted(machines.keys()):
			shutit_session = shutit_sessions[machine]
			shutit_session.send('sudo useradd -s /bin/bash -d /opt/stack -m stack')
			shutit_session.send('echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/stack')
			shutit_session.login('sudo su - stack')
			shutit_session.send('git clone https://github.com/openstack-dev/devstack.git -b stable/pike devstack/')
			shutit_session.send('cd devstack')
			ip = shutit_session[ip]
			shutit_session.send('''cat > local.conf <<EOF
[[local|localrc]]
ADMIN_PASSWORD=secret
DATABASE_PASSWORD=\$ADMIN_PASSWORD
RABBIT_PASSWORD=\$ADMIN_PASSWORD
SERVICE_PASSWORD=\$ADMIN_PASSWORD
HOST_IP=''' + ip + '''
RECLONE=yes
EOF''')
			shutit_session.send('./stack.sh')
			shutit_session.pause_point()


		return True


	def get_config(self, shutit):
		shutit.get_config(self.module_id,'vagrant_image',default='ubuntu/xenial64')
		shutit.get_config(self.module_id,'vagrant_provider',default='virtualbox')
		shutit.get_config(self.module_id,'gui',default='true')
		shutit.get_config(self.module_id,'memory',default='8192')
		shutit.get_config(self.module_id,'swapsize',default='2G')
		return True

	def test(self, shutit):
		return True

	def finalize(self, shutit):
		return True

	def is_installed(self, shutit):
		return False

	def start(self, shutit):
		return True

	def stop(self, shutit):
		return True

def module():
	return shutit_openstack(
		'git.shutit_openstack.shutit_openstack', 1189802658.0001,
		description='',
		maintainer='',
		delivery_methods=['bash'],
		depends=['shutit.tk.setup','shutit-library.virtualization.virtualization.virtualization','tk.shutit.vagrant.vagrant.vagrant']
	)
