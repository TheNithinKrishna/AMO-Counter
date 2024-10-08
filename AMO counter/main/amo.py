"""FILE CONTAINS THE AMO Acceptance MAIN FUNCTION which is used to run the acceptance"""
import logging
import datetime
import time
import sender
import ctypes
from random import randint
from helper.amo import amo
from stdlib.creds import email_cred
from stdlib.utility import successmessageconditionalyaccept,client_mail_send,zipcode_check,inactive_inDB,capacity_mail_send,send_login_error_mail,ignored_order,write_to_db,send_accepted_mail,cursorexec,exception_mail_send,logger_portal
import sys

email_creds=email_cred()

portal_name='AMO'
userid = sys.argv[1]
# userid = '263214'
def main():    
    count = 0    
    while True:
        try:
            client_data=cursorexec("order_acceptance","SELECT",f"""SELECT * FROM `AMO` WHERE  `userid` = '{userid}' LIMIT 1""") #fetch corrosponding client details from database
            ctypes.windll.kernel32.SetConsoleTitleW(f"{client_data['Client_name']}-AMO")
            if count == 0:
                count += 1
                logger_portal(client_data['Client_name'],portal_name)    
            init=amo(client_data,portal_name)                     
            cursorexec("order_updation",'UPDATE',f"""UPDATE `servercheck` SET `event`='{datetime.datetime.now()}' where `portal`='{portal_name}' """)
            if client_data:
                logging.info("%s acceptor for %s",portal_name,client_data['Client_name'])
                if client_data['Status'] == 'Active': #check if client is Active
                    logging.info('Client Active')
                    session,session_flag=init.session_check() #Check session is active or not
                    capacity_check=False
                    if session_flag:
                        accepted = []
                        ignored=[]
                        countered=[]
                        session,availbleorders=init.checkorder_portal() #check available orders from portal
                        if availbleorders['records'] >0:
                            order_received_time=datetime.datetime.now()
                            for avail_order in availbleorders['rows']:
                                common_db_data=cursorexec("order_updation",'SELECT',"""SELECT * FROM `common_data_acceptance` """)
                                to_accept,due_date,session,criteriaflag,address,fee_portal=init.criteria_check(avail_order) #checking accepting criteria with database
                                if criteriaflag:
                                    flag_check=init.accept_order(to_accept,due_date) #Accepting order if criteria satisfied
                                    if flag_check=='accept':
                                        accepted.append({'to_accept':to_accept,"due_date":due_date, "fee_portal":fee_portal, "Address":address,"Ordertype":to_accept['VendorProduct'],"order_received_time":order_received_time}) #Appending accepted orders
                                    elif flag_check=="capacity":
                                        capacity_check=True
                                        ignored.append({'to_accept':to_accept,'ignoredmsg':'Client Capacity Exceeded','fee_portal':fee_portal,"session":session,'client_data':client_data,'Address':address,"order_received_time":order_received_time})
                                        logging.info(flag_check)
                                    else:
                                        ignored.append({'to_accept':to_accept,'ignoredmsg':'Order Expired','fee_portal':fee_portal,"session":session,'client_data':client_data,'Address':address,"order_received_time":order_received_time})
                                        logging.info(flag_check)
                                else:
                                    if due_date=="Order price Not satisfied" and client_data['order_quote_status']=='ON':
                                        zipcode_check_flag=zipcode_check(to_accept['SubjectPropertyPostalCode'],to_accept['VendorProduct'],fee_portal,client_data,portal_name)
                                        if zipcode_check_flag:
                                            feeaccept_flag,requested_fee,due_date=init.add_counter_fee(to_accept,session,common_db_data)
                                            if feeaccept_flag:                                                                    
                                                countered.append({"order":to_accept, "address":address,"requested_fee":requested_fee,"due_date":due_date,"fee_portal":fee_portal,"order_type":to_accept['VendorProduct'],"order_id":to_accept['OrderID'],"order_received_time":order_received_time})
                                            else:
                                                ignored.append({'to_accept':to_accept,'ignoredmsg':'Order Expired','Address':address,'fee_portal':fee_portal,"session":session,'client_data':client_data,'Zipcode':to_accept['SubjectPropertyPostalCode'],"order_received_time":order_received_time})
                                                logging.info("Could not counter the order")
                                        else:
                                            ignored.append({'to_accept':to_accept,'ignoredmsg':'Zipcode Not Satisfied','Address':address,'fee_portal':fee_portal,"session":session,'client_data':client_data,'Zipcode':to_accept['SubjectPropertyPostalCode'],"order_received_time":order_received_time})
                                    else:
                                        ignored.append({'to_accept':to_accept,'ignoredmsg':due_date,'Address':address,'fee_portal':fee_portal,"session":session,'client_data':client_data,'Zipcode':to_accept['SubjectPropertyPostalCode'],"order_received_time":order_received_time})
                                

                            for accept in accepted:
                                subject=f'{portal_name} order Accepted!'
                                order_details=accept['to_accept']
                                mail_status=send_accepted_mail(accept['due_date'], accept['fee_portal'],order_details['VendorProduct'], accept['Address'],order_details['OrderID'],client_data['from_mail'],client_data['to_clientMail'],client_data['to_ecesisMail'],client_data['Client_name'],subject,portal_name) #function to sending accepted orders to client
                                time.sleep(5)
                                write_to_db(client_data,str(datetime.datetime.now()),accept['due_date'],portal_name,accept['fee_portal'],order_details['VendorProduct'],accept["Address"],mail_status,portal_name,order_details['OrderID'],subject,accept['order_received_time']) #function to insert accepted orders to database
                            
                            for avail_order in countered:
                                try:                                
                                    subject='Fee Requested!! - AMO'
                                    logging.info('Fee Requested!! - AMO {}'.format(avail_order['address']))
                                    if client_data['from_mail'] == 'notificationalert@bpoacceptor.com' or client_data['from_mail'] == 'bangrealty@bpoacceptor.com' or client_data['from_mail'] == 'keystoneholding@bpoacceptor.com' or client_data['from_mail'] == 'notifications@bpoacceptor.com' or client_data['from_mail'] == 'info@bpoacceptor.com':
                                        from_mail_id = client_data['from_mail']
                                        logging.info(f"from mail : {from_mail_id}")
                                        mail = sender.Mail('smtp.gmail.com', from_mail_id, email_creds[from_mail_id], 465, use_ssl=True,fromaddr=from_mail_id)                                 
                                    else:    
                                        from_mail_id = 'info@bpoacceptor.com'
                                        logging.info(f"from mail : {from_mail_id}")
                                        mail = sender.Mail('smtp.gmail.com', from_mail_id, email_creds[from_mail_id], 465, use_ssl=True,fromaddr=from_mail_id) 
                                    mail_message_body=successmessageconditionalyaccept(client_data['Client_name'],str(datetime.datetime.now()), avail_order['due_date'], "amo", avail_order['fee_portal'], avail_order['order_type'], avail_order['address'],avail_order['order_id'],requested_fee,"Fee Requested")
                                    client_mail_send(mail,client_data['to_clientMail'],client_data['to_ecesisMail'],subject,mail_message_body)
                                    mail_status='Countered'
                                    logging.info('Countered')
                                    write_to_db(client_data,str(datetime.datetime.now()),avail_order['due_date'],'amo',fee_portal,avail_order['order_type'],avail_order['address'],mail_status,portal_name,avail_order['order_id'],subject,avail_order['order_received_time'])
                                except Exception as ex:
                                    print(ex)
                                    mail_status='Countered'
                                    write_to_db(client_data,str(datetime.datetime.now()),avail_order['due_date'],'amo',fee_portal,avail_order['order_type'],avail_order['address'],mail_status,portal_name,avail_order['order_id'],subject,avail_order['order_received_time'])
                                    logging.info('Exception Here: {}'.format(ex))    
                                
                            for ignore in ignored:
                                order_details=ignore['to_accept']

                                zipcode = order_details['SubjectPropertyPostalCode']
                                if '-' in zipcode:
                                    zipcode=zipcode.split("-")[0]

                                subject=f"Ignored Order!!! - {portal_name}-{ignore['ignoredmsg']}"
                                logging.info(subject)
                                ignored_order(ignore['Address'],order_details['VendorProduct'],ignore['ignoredmsg'],ignore['fee_portal'],ignore['client_data'],portal_name,zipcode,subject,ignore['order_received_time']) #function to send ignored orders mail to client
                            if capacity_check:
                                capacity_mail_send(client_data['Client_name'],portal_name) #function to send capacity exceeded orders
                        else:
                            logging.info('No Orders Available in Portal')
                                
                        random_sleep_time = randint(3,6)
                        logging.info('New order will be checked after %s',random_sleep_time)
                        time.sleep(random_sleep_time)
                    else:
                        try:
                            send_login_error_mail(portal_name,client_data) #function for sending login error
                            #make client inactive in DB
                            logging.info('Making Client Inactive in DB')
                            cursorexec("order_acceptance","UPDATE",f"UPDATE `{portal_name}` SET `Status`='Inactive' , `comments`='Login Failed' WHERE userid = '{client_data['userid']}' LIMIT 1")

                        except Exception as ex:
                            exception_mail_send(portal_name,portal_name,ex)
                            logging.info(ex)
                else:
                    logging.info('Client Inactive..Waiting 30 minutes before checking DB')
                    inactive_inDB(client_data['Client_name'],portal_name)
                    time.sleep(1800)#wait for 30 minutes and continue loop
            else:
                logging.info('Unable to map the client data with DB')
                ex= 'Unable to map the {} with DB for autoacceptance for the AMO portal'.format(userid)
                exception_mail_send(client_data,portal_name,ex) 
                
            start_time,end_time = int(client_data['random_sleep_time'].split(',')[0]),int(client_data['random_sleep_time'].split(',')[1])
            random_sleep_time = randint(start_time,end_time)
            logging.info('New order will be checked after %s',random_sleep_time)
            time.sleep(random_sleep_time)   
                            
        except Exception as ex:
            #reconnect and continue loop from beginning
            time.sleep(30)
            exception_mail_send(portal_name,portal_name,ex)
            logging.info(ex)
            #cursor=get_cursor("order_acceptance").reconnect(attempts=2, delay=1)
            continue
if __name__ == "__main__":
    main()
