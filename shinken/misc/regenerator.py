#!/usr/bin/python
#Copyright (C) 2009 Gabes Jean, naparuba@gmail.com
#
#This file is part of Shinken.
#
#Shinken is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#Shinken is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU Affero General Public License for more details.
#
#You should have received a copy of the GNU Affero General Public License
#along with Shinken.  If not, see <http://www.gnu.org/licenses/>.

import time

# Import all obejcts we will need
from shinken.objects import Host, Hosts
from shinken.objects import Hostgroup, Hostgroups
from shinken.objects import Service, Services
from shinken.objects import Servicegroup, Servicegroups
from shinken.objects import Contact, Contacts
from shinken.objects import Contactgroup, Contactgroups
from shinken.objects import NotificationWay, NotificationWays
from shinken.objects import Timeperiod, Timeperiods
from shinken.objects import Command, Commands
from shinken.objects import Config
from shinken.schedulerlink import SchedulerLink, SchedulerLinks
from shinken.reactionnerlink import ReactionnerLink, ReactionnerLinks
from shinken.pollerlink import PollerLink, PollerLinks
from shinken.brokerlink import BrokerLink, BrokerLinks




# Class for a Regenerator. It will get broks, and "regenerate" real obejcts
# from them :)
class Regenerator:
    def __init__(self):

        # Our Real datas
        self.configs = {}
        self.hosts = Hosts([])
        self.services = Services([])
        self.notificationways = NotificationWays([])
        self.contacts = Contacts([])
        self.hostgroups = Hostgroups([])
        self.servicegroups = Servicegroups([])
        self.contactgroups = Contactgroups([])
        self.timeperiods = Timeperiods([])
        self.commands = Commands([])
        self.schedulers = SchedulerLinks([])
        self.pollers = PollerLinks([])
        self.reactionners = ReactionnerLinks([])
        self.brokers = BrokerLinks([])

        # And in progress one
        self.inp_hosts = {}
        self.inp_services = {}
        self.inp_hostgroups = {}
        self.inp_servicegroups = {}
        self.inp_contactgroups = {}

        # Do not ask for full data resent too much
        self.last_need_data_send = time.time()


    def manage_brok(self, brok):
        """ Look for a manager function for a brok, and call it """
        manage = getattr(self, 'manage_' + brok.type + '_brok', None)
        if manage:
            return manage(brok)


    def update_element(self, e, data):
        for prop in data:
            setattr(e, prop, data[prop])


    def create_reversed_list(self):
        self.hosts.create_reversed_list()
        self.hostgroups.create_reversed_list()
        self.contacts.create_reversed_list()
        self.contactgroups.create_reversed_list()
        self.notificationways.create_reversed_list()
        self.services.create_reversed_list()
        self.servicegroups.create_reversed_list()
        self.timeperiods.create_reversed_list()
        #self.modules.create_reversed_list()
        #self.resultmodulations.create_reversed_list()
        #self.criticitymodulations.create_reversed_list()
        #self.escalations.create_reversed_list()
        #self.discoveryrules.create_reversed_list()
        #self.discoveryruns.create_reversed_list()
        self.commands.create_reversed_list()


    def set_schedulingitem_values(self, i):
        return
        i.check_period = self.get_timeperiod(i.check_period)
        i.notification_period = self.get_timeperiod(i.notification_period)
        i.contacts = self.get_contacts(i.contacts)
        i.rebuild_ref()


    # Now we get all data about an instance, link all this stuff :)
    def all_done_linking(self, inst_id):
        print "In ALL Done linking phase for instance", inst_id
        # check if the instance is really defined, so got ALL the
        # init phase
        if not inst_id in self.configs.keys():
            print "Warning : the instance %d is not fully given, bailout" % inst_id
            return

        # Try to load the in progress list and make them available for 
        # finding
        try:
            inp_hosts = self.inp_hosts[inst_id]
            inp_hosts.create_reversed_list()
            inp_hostgroups = self.inp_hostgroups[inst_id]
            #inp_hostgroups.create_reversed_list()
            inp_contactgroups = self.inp_contactgroups[inst_id]
            inp_contactgroups.create_reversed_list()
        except Exception, exp:
            print "Warning all done: ", exp
            return


        # Link HOSTGROUPS with hosts
        for hg in inp_hostgroups:
            new_members = []
            for (i, hname) in hg.members:
                h = inp_hosts.find_by_name(hname)
                if h:
                    new_members.append(h)
            hg.members = new_members

        # Merge HOSTGROUPS with real ones
        for inphg in inp_hostgroups:
            hgname = inphg.hostgroup_name
            hg = self.hostgroups.find_by_name(hgname)
            # If hte hostgroup already exist, just add the new
            # hosts into it
            if hg:
                hg.members.extend(inphg.members)
            else: # else take the new one
                self.hostgroups[inphg.id] = inphg
        # We can delare hostgroups done
        self.hostgroups.create_reversed_list()
                
        # Now link HOSTS with hostgroups, and commands
        for h in inp_hosts:
            #print "Linking %s groups %s" % (h.get_name(), h.hostgroups)
            new_hostgroups = []
            for hgname in h.hostgroups.split(','):
                hg = self.hostgroups.find_by_name(hgname)
                if hg:
                    new_hostgroups.append(hg)
            h.hostgroups = new_hostgroups
            
            # Now link Command() objects
            self.linkify_a_command(h, 'check_command')
            self.linkify_a_command(h, 'event_handler')
            
            # Now link timeperiods
            self.linkify_a_timeperiod(h, 'notification_period')
            self.linkify_a_timeperiod(h, 'check_period')
            self.linkify_a_timeperiod(h, 'maintenance_period')

            # And link contacts too
            self.linkify_contacts(h, 'contacts')

            # We can really declare this host OK now
            self.hosts[h.id] = h

        self.hosts.create_reversed_list()

        # Linking TIMEPERIOD exclude with real ones now
        for tp in self.timeperiods:
            new_exclude = []
            for ex in tp.exclude:
                exname = ex.timeperiod_name
                t = self.timeperiods(exname)
                if t:
                    new_exclude.append(t)
            tp.exclude = new_exclude


        # Link CONTACTGROUPS with contacts
        for cg in inp_contactgroups:
            new_members = []
            for (i, cname) in cg.members:
                c = self.contacts.find_by_name(cname)
                if c:
                    new_members.append(c)
            cg.members = new_members

        # Merge contactgroups with real ones
        for inpcg in inp_contactgroups:
            cgname = inpcg.contactgroup_name
            cg = self.contactgroups.find_by_name(cgname)
            # If the contactgroup already exist, just add the new
            # contacts into it
            if cg:
                cg.members.extend(inpcg.members)
            else: # else take the new one
                self.contactgroups[inpcg.id] = inpcg
        # We can delare contactgroups done
        self.contactgroups.create_reversed_list()


        # Ok, we can regenerate ALL find list, so your clietns will
        # see new objects now
#        self.create_reversed_list()            



    # We look for o.prop (CommandCall) and we link the inner
    # Command() object with our real ones
    def linkify_a_command(self, o, prop):
        cc = getattr(o, prop)
        # if the command call is void, bypass it
        if not cc:
            return
        cmdname = cc.command.command_name
        c = self.commands.find_by_name(cmdname)
        if c:
            cc.command = c


    # We look at o.prop and for each command we relink it
    def linkify_commands(self, o, prop):
        v = getattr(o, prop)
        if not v:
            return

        for cc in v:
            cmdname = cc.command.command_name
            c = self.commands.find_by_name(cmdname)
            if c:
                cc.command = c
        


    # We look at the timeperiod() object of o.prop
    # and we replace it with our true one
    def linkify_a_timeperiod(self, o, prop):
        t = getattr(o, prop)
        if not t:
            return
        tpname = t.timeperiod_name
        tp = self.timeperiods.find_by_name(tpname)
        if tp:
            print "Seeting", prop, tp.get_name(), 'of', o.get_name()
            setattr(o, prop, tp)
            

    # We look at o.prop and for each contacts in it,
    # we replace it with true object in self.contacts
    def linkify_contacts(self, o, prop):
        v = getattr(o, prop)

        if not v:
            return

        new_v = []
        for oc in v:
            cname = oc.contact_name
            c = self.contacts.find_by_name(cname)
            if c:
                new_v.append(c)
        setattr(o, prop, new_v)
                


############### Brok management part

    def manage_program_status_brok(self, b):
        data = b.data
        c_id = data['instance_id']
        print "Regenerator : Creating config:", c_id
        
        # We get a real Conf object ,adn put our data
        c = Config()
        self.update_element(c, data)
        #for prop in data:
        #    setattr(c, prop, data[prop])

        # Clean all in_progress things.
        # And in progress one
        self.inp_hosts[c_id] = Hosts([])
        self.inp_services[c_id] = Services([])
        self.inp_hostgroups[c_id] = Hostgroups([])
        self.inp_servicegroups[c_id] = Servicegroups([])
        self.inp_contactgroups[c_id] = Contactgroups([])

        # And we save it
        self.configs[c_id] = c

        ##Clean the old "hard" objects

        # We should clean all previously added hosts and services
        print "Clean hosts/service of", c_id
        to_del_h = [h for h in self.hosts if h.instance_id == c_id]
        to_del_srv = [s for s in self.services if s.instance_id == c_id]

        print "Cleaning host:%d srv:%d" % (len(to_del_h), len(to_del_srv))
        # Clean hosts from hosts and hostgroups
        for h in to_del_h:
            print "Deleting", h.get_name()
            del self.hosts[h.id]

        # Now clean all hostgroups too
        for hg in self.hostgroups:
            print "Cleaning hostgroup %s:%d" % (hg.get_name(), len(hg.members))
            # Exclude from members the hosts with this inst_id
            hg.members = [h for h in hg.members if h.instance_id != inst_id]
            print "Len after", len(hg.members)

        for s in to_del_srv:
            print "Deleting", s.gt_dbg_name()
            del self.services[s.id]

        # Now clean service groups
        for sg in self.servicegroups:
            sg.members = [s for s in sg.members if s.instance_id != inst_id]

        # We now regererate reversed list so the client will find only real objects
        self.create_reversed_list()


    def manage_update_program_status_brok(self, b):
        data = b.data
        c_id = data['instance_id']

        # If we got an update about an unknow isntance, cry and ask for a full
        # version!
        if c_id not in self.instance_ids:
            # Do not ask data too quickly, very dangerous
            # one a minute
            if time.time() - self.last_need_data_send > 60:
                print "I ask the broker for instance id data :", c_id
                msg = Message(id=0, type='NeedData', data={'full_instance_id' : c_id})
                self.from_q.put(msg)
                self.last_need_data_send = time.time()
            return

        # We have only one config here, with id 0
        c = self.configs[c_id]
        self.update_element(c, data)
            

    # Get a new host. Add in in in progress tab
    def manage_initial_host_status_brok(self, b):
        data = b.data
        hname = data['host_name']
        inst_id = data['instance_id']

        # Try to get the inp progress Hosts
        try:
            inp_hosts = self.inp_hosts[inst_id]
        except Exception, exp: #not good. we will cry in theprogram update
            print "Not good!", exp
            return

        print "Creating an host: %s in instance %d" % (hname, inst_id)

        h = Host({})
        self.update_element(h, data)        

        # We need to rebuild Downtime and Comment relationship
        for dtc in h.downtimes + h.comments:
            dtc.ref = h

        # Ok, put in in the in progress hosts
        inp_hosts[h.id] = h



    #In fact, an update of a host is like a check return
    def manage_update_host_status_brok(self, b):
        self.manage_host_check_result_brok(b)
        data = b.data
        host_name = data['host_name']
        #In the status, we've got duplicated item, we must relink thems
        try:
            h = self.hosts[host_name]
        except KeyError:
            print "Warning : the host %s is unknown!" % host_name
            return
        self.update_element(h, data)
        self.set_schedulingitem_values(h)
        for dtc in h.downtimes + h.comments:
            dtc.ref = h
        self.livestatus.count_event('host_checks')


    # From now we only create an hostgroup in the in prepare
    # part. We will link at the end.
    def manage_initial_hostgroup_status_brok(self, b):
        data = b.data
        hgname = data['hostgroup_name']
        inst_id = data['instance_id']
        
        # Try to get the inp progress Hostgroups
        try:
            inp_hostgroups = self.inp_hostgroups[inst_id]
        except Exception, exp: #not good. we will cry in theprogram update
            print "Not good!", exp
            return

        print "Creating an hostgroup: %s in instance %d" % (hgname, inst_id)
        
        # With void members
        hg = Hostgroup([])

        # populate data
        self.update_element(hg, data)

        # We will link hosts into hostgroups later
        # so now only save it
        inp_hostgroups[hg.id] = hg


    def manage_initial_service_status_brok(self, b):
        data = b.data
        s_id = data['id']
        host_name = data['host_name']
        service_description = data['service_description']
        inst_id = data['instance_id']
        
        #print "Creating Service:", s_id, data
        s = Service({})
        s.instance_id = inst_id

        self.update_element(s, data)
        self.set_schedulingitem_values(s)
        
        try:
            h = self.hosts[host_name]
            # Reconstruct the connection between hosts and services
            h.services.append(s)
            # There is already a s.host_name, but a reference to the h object can be useful too
            s.host = h
        except Exception:
            return
        for dtc in s.downtimes + s.comments:
            dtc.ref = s
        self.services[host_name+service_description] = s
        #self.number_of_objects += 1
        # We need this for manage_initial_servicegroup_status_brok where it
        # will speed things up dramatically


    #In fact, an update of a service is like a check return
    def manage_update_service_status_brok(self, b):
        self.manage_service_check_result_brok(b)
        data = b.data
        host_name = data['host_name']
        service_description = data['service_description']
        #In the status, we've got duplicated item, we must relink thems
        try:
            s = self.services[host_name+service_description]
        except KeyError:
            print "Warning : the service %s/%s is unknown!" % (host_name, service_description)
            return
        self.update_element(s, data)
        self.set_schedulingitem_values(s)
        for dtc in s.downtimes + s.comments:
            dtc.ref = s
   


    def manage_initial_servicegroup_status_brok(self, b):
        data = b.data
        sg_id = data['id']
        servicegroup_name = data['servicegroup_name']
        members = data['members']
        del data['members']

        # Like for hostgroups, maybe we already got this
        # service group from another instance, need to
        # factorize all
        try:
            sg = self.servicegroups[servicegroup_name]
        except KeyError:
            #print "Creating servicegroup:", sg_id, data
            sg = Servicegroup()
            # By default set members as a void list
            setattr(sg, 'members', [])

        self.update_element(sg, data)

        for (s_id, s_name) in members:
            # A direct lookup by s_host_name+s_name is not possible
            # because we don't have the host_name in members, only ids.
            try:
                sg.members.append(self.service_id_cache[s_id])
            except Exception:
                pass

        sg.members = list(set(sg.members))
        self.servicegroups[servicegroup_name] = sg
        #self.number_of_objects += 1


    # For Contacts, it's a global value, so 2 cases :
    # We got it -> we update it
    # We don't -> we crete it
    # In both cases we need to relink it
    def manage_initial_contact_status_brok(self, b):
        data = b.data
        cname = data['contact_name']
        print "Contact with data", data
        c = self.contacts.find_by_name(cname)
        if c:
            self.update_element(c, data)
        else:
            print "Creating Contact:", cname
            c = Contact({})
            self.update_element(c, data)
            self.contacts[c.id] = c
        
        # Delete some useless contact values
        del c.host_notification_commands
        del c.service_notification_commands
        del c.host_notification_period
        del c.service_notification_period

        # Now manage notification ways too
        # Same than for cotnacts. We create or
        # update
        nws = c.notificationways
        print "Got notif ways", nws
        new_notifways = []
        for cnw in nws:
            nwname = cnw.notificationway_name
            nw = self.notificationways.find_by_name(nwname)
            if not nw:
                print "Creating notif way", nwname
                nw = NotificationWay([])
                self.notificationways[nw.id] = nw
            # Now update it
            for prop in NotificationWay.properties:
                if hasattr(cnw, prop):
                    setattr(nw, prop, getattr(cnw, prop))
            new_notifways.append(nw)
            
            # Linking the notification way
            # With commands
            self.linkify_commands(nw, 'host_notification_commands')
            self.linkify_commands(nw, 'service_notification_commands')
            
            
            # Now link timeperiods
            self.linkify_a_timeperiod(nw, 'host_notification_period')
            self.linkify_a_timeperiod(nw, 'service_notification_period')

        c.notificationways = new_notifways

        # Ok, declare this contact now :)
        # And notif ways too
        self.contacts.create_reversed_list()
        self.notificationways.create_reversed_list()


    # From now we only create an hostgroup with unlink data in the
    # in prepare list. We will link all of them at the end.
    def manage_initial_contactgroup_status_brok(self, b):
        data = b.data
        cgname = data['contactgroup_name']
        inst_id = data['instance_id']
        
        # Try to get the inp progress Contactgroups
        try:
            inp_contactgroups = self.inp_contactgroups[inst_id]
        except Exception, exp: #not good. we will cry in theprogram update
            print "Not good!", exp
            return

        print "Creating an contactgroup: %s in instance %d" % (cgname, inst_id)
        
        # With void members
        cg = Contactgroup([])

        # populate data
        self.update_element(cg, data)

        # We will link hosts into hostgroups later
        # so now only save it
        inp_contactgroups[cg.id] = cg



    # For Timeperiods we got 2 cases : do we already got the command or not.
    # if got : just update it
    # if not : create it and delacre it in our main commands
    def manage_initial_timeperiod_status_brok(self, b):
        data = b.data
        print "Creatin timeperiod", data
        tpname = data['timeperiod_name']
        
        tp = self.timeperiods.find_by_name(tpname)
        if tp:
            # print "Already exisintg timeperiod", tpname
            self.update_element(tp, data)
        else:
            print "Creating Timeperiod:", tpname
            tp = Timeperiod({})
            self.update_element(tp, data)
            self.timeperiods[tp.id] = tp
            self.timeperiods.create_reversed_list()


    # For command we got 2 cases : do we already got the command or not.
    # if got : just update it
    # if not : create it and delacre it in our main commands
    def manage_initial_command_status_brok(self, b):
        data = b.data
        cname = data['command_name']
        
        c = self.commands.find_by_name(cname)
        if c:
            #print "Already existing command", cname, "updating it"
            self.update_element(c, data)
        else:
            #print "Creating a new command", cname
            c = Command({})
            self.update_element(c, data)
            self.commands[c.id] = c
            # Ok, we can regenerate the reversed list so
            self.commands.create_reversed_list()


    def manage_initial_scheduler_status_brok(self, b):
        data = b.data
        scheduler_name = data['scheduler_name']
        print "Creating Scheduler:", scheduler_name, data
        sched = SchedulerLink({})
        print "Created a new scheduler", sched
        self.update_element(sched, data)
        print "Updated scheduler"
        #print "CMD:", c
        self.schedulers[scheduler_name] = sched
        print "scheduler added"
        #print "MONCUL: Add a new scheduler ", sched
        #self.number_of_objects += 1


    def manage_update_scheduler_status_brok(self, b):
        data = b.data
        scheduler_name = data['scheduler_name']
        try:
            s = self.schedulers[scheduler_name]
            self.update_element(s, data)
            #print "S:", s
        except Exception:
            pass


    def manage_initial_poller_status_brok(self, b):
        data = b.data
        poller_name = data['poller_name']
        print "Creating Poller:", poller_name, data
        poller = PollerLink({})
        print "Created a new poller", poller
        self.update_element(poller, data)
        print "Updated poller"
        #print "CMD:", c
        self.pollers[poller_name] = poller
        print "poller added"
        #print "MONCUL: Add a new scheduler ", sched
        #self.number_of_objects += 1


    def manage_update_poller_status_brok(self, b):
        data = b.data
        poller_name = data['poller_name']
        try:
            s = self.pollers[poller_name]
            self.update_element(s, data)
        except Exception:
            pass


    def manage_initial_reactionner_status_brok(self, b):
        data = b.data
        reactionner_name = data['reactionner_name']
        print "Creating Reactionner:", reactionner_name, data
        reac = ReactionnerLink({})
        print "Created a new reactionner", reac
        self.update_element(reac, data)
        print "Updated reactionner"
        #print "CMD:", c
        self.reactionners[reactionner_name] = reac
        print "reactionner added"
        #print "MONCUL: Add a new scheduler ", sched
        #self.number_of_objects += 1


    def manage_update_reactionner_status_brok(self, b):
        data = b.data
        reactionner_name = data['reactionner_name']
        try:
            s = self.reactionners[reactionner_name]
            self.update_element(s, data)
        except Exception:
            pass


    def manage_initial_broker_status_brok(self, b):
        data = b.data
        broker_name = data['broker_name']
        print "Creating Broker:", broker_name, data
        broker = BrokerLink({})
        print "Created a new broker", broker
        self.update_element(broker, data)
        print "Updated broker"
        #print "CMD:", c
        self.brokers[broker_name] = broker
        print "broker added"
        #print "MONCUL: Add a new scheduler ", sched
        #self.number_of_objects += 1


    def manage_update_broker_status_brok(self, b):
        data = b.data
        broker_name = data['broker_name']
        try:
            s = self.brokers[broker_name]
            self.update_element(s, data)
        except Exception:
            pass


    #A service check have just arrived, we UPDATE data info with this
    def manage_service_check_result_brok(self, b):
        data = b.data
        host_name = data['host_name']
        service_description = data['service_description']
        try:
            s = self.services[host_name+service_description]
            self.update_element(s, data)
        except Exception:
            pass


    #A service check update have just arrived, we UPDATE data info with this
    def manage_service_next_schedule_brok(self, b):
        self.manage_service_check_result_brok(b)


    def manage_host_check_result_brok(self, b):
        data = b.data
        host_name = data['host_name']
        try:
            h = self.hosts[host_name]
            self.update_element(h, data)
        except Exception:
            pass


    # this brok should arrive within a second after the host_check_result_brok
    def manage_host_next_schedule_brok(self, b):
        self.manage_host_check_result_brok(b)


    
    def manage_initial_broks_done_brok(self, b):
        inst_id = b.data['instance_id']
        print "Finish the configuration of instance", inst_id
        
        self.all_done_linking(inst_id)


        