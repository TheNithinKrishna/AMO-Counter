"""FILE CONTAINS THE Valuation Connect MAIN FUNCTIONS"""
import logging
import datetime
import time
import ctypes
from random import randint
from helper.ca import ca
import sys
from stdlib.utility import write_to_db,cursorexec,inactive_inDB,logger_mail,send_login_error_mail,ignored_order,exception_mail_send,send_accepted_mail,capacity_mail_send,zipcode_check,check_counter_accepted
portal_name='Consolidate Analytics'

userid = sys.argv[1]

# userid = '580993'

def main():    
    count = 0
    while True:
        try:
            if count == 0:
                count += 1
                logger_mail(portal_name)
            init=ca("",portal_name)
            cursorexec("order_updation",'UPDATE',f"""UPDATE `servercheck` SET
                                `event`='{datetime.datetime.now()}' where `portal`='CA' """)
            # orders_found=init.checkorder_mail() #function to Check new order mail notification
            client_data=cursorexec("order_acceptance","SELECT",f"""SELECT * FROM `ca` WHERE  {userid} = userid LIMIT 1""") #fetch corrosponding client details from database
            init.client_data=client_data
            ctypes.windll.kernel32.SetConsoleTitleW(f"{client_data['Client_name']}-CA")
            if client_data:
                logging.info("%s acceptor for %s",portal_name,client_data['Client_name'])
                if client_data['Status'] == 'Active': #check if client is Active
                    logging.info('Client Active')
                    session,session_flag=init.session_check() #Check session is active or not
                    capacity_check=False
                    if session_flag:
                        accepted = []
                        ignored=[]
                        session,availbleorders=init.checkorder_portal() #check available orders from portal
                        if availbleorders['records']>0:
                            order_received_time=datetime.datetime.now()
                            for avail_order in availbleorders['rows']:
                                to_accept,due_date,session,criteriaflag,address,fee_portal,due_diff,due_date_counter=init.criteria_check(avail_order) #checking accepting criteria with database
                                if criteriaflag:
                                    flag_check=init.accept_order(to_accept,due_date) #Accepting order if criteria satisfied
                                    if flag_check=='accept':
                                        accepted.append({"due_date":due_date, "fee_portal":fee_portal, "Address":address,"Ordertype":to_accept['VendorProduct'],"order_id":to_accept['OrderID'],"order_received_time":order_received_time}) #Appending accepted orders
                                    elif flag_check=="capacity":
                                        capacity_check=True
                                        ignored.append({'to_accept':to_accept,'ignoredmsg':'Client Capacity Exceeded','fee_portal':fee_portal,"session":session,'client_data':client_data,'Address':address, 'due_diff':due_diff,"due_date":due_date_counter,"order_received_time":order_received_time})
                                        logging.info(flag_check)
                                    else:
                                        ignored.append({'to_accept':to_accept,'ignoredmsg':'Order Expired','fee_portal':fee_portal,"session":session,'client_data':client_data,'Address':address, 'due_diff':due_diff,"due_date":due_date_counter,"order_received_time":order_received_time})
                                        logging.info(flag_check)
                                else:
                                    ignored.append({'to_accept':to_accept,'ignoredmsg':due_date,'fee_portal':fee_portal,"session":session,'client_data':client_data,'Address':address, 'due_diff':due_diff,"due_date":due_date_counter,"order_received_time":order_received_time}) #Appending ignored orders                                    

                            for accept in accepted:
                                subject=f'{portal_name} order Accepted!'
                                mail_status=send_accepted_mail(accept['due_date'], accept['fee_portal'],accept['Ordertype'], accept['Address'],accept['order_id'],client_data['from_mail'],client_data['to_clientMail'],client_data['to_ecesisMail'],client_data['Client_name'],subject,portal_name) #function to sending accepted orders to client
                                time.sleep(5)
                                write_to_db(client_data,str(datetime.datetime.now()),accept['due_date'],portal_name,accept['fee_portal'],accept['Ordertype'],accept["Address"],mail_status,portal_name,accept['order_id'],subject,accept['order_received_time']) #function to insert accepted orders to database
                            for ignored in ignored:
                                order_details=ignored['to_accept']

                                zipcode = order_details['SubjectPropertyPostalCode']
                                if '-' in zipcode:
                                    zipcode=zipcode.split("-")[0]
                                
                                if 'order price not satisfied' in str(ignored['ignoredmsg']).lower() and client_data['order_quote_status']=="ON":
                                    zipcheck_flag=zipcode_check(zipcode,order_details['VendorProduct'],ignored['fee_portal'],client_data,portal_name)
                                    if zipcheck_flag:
                                        if ignored['due_diff'] > 0:
                                            init.add_counter_fee(ignored) ### for ferequesting the order if the price not satisfied
                                        else:
                                            subject=f"Ignored Order!!! - {portal_name}-{'Due Date Not Satisfied'}"
                                            ignored_order(ignored['Address'],order_details['VendorProduct'],'Due Date Not Satisfied',ignored['fee_portal'],ignored['client_data'],portal_name,zipcode,subject,ignored['order_received_time']) #function to send ignored orders mail to client
                                    else:
                                        subject=f"Ignored Order!!! - {portal_name}-{'Zipcode not satisfied'}"
                                        ignored_order(ignored['Address'],order_details['VendorProduct'],'Zipcode not satisfied',ignored['fee_portal'],ignored['client_data'],portal_name,zipcode,subject,ignored['order_received_time']) #function to send ignored orders mail to client                                            
                                else:
                                    subject=f"Ignored Order!!! - {portal_name}-{ignored['ignoredmsg']}"
                                    logging.info(subject)
                                    ignored_order(ignored['Address'],order_details['VendorProduct'],ignored['ignoredmsg'],ignored['fee_portal'],ignored['client_data'],portal_name,zipcode,subject,ignored['order_received_time']) #function to send ignored orders mail to client
                            if capacity_check:
                                capacity_mail_send(client_data['Client_name'],portal_name) #function to send capacity exceeded orders
                            # random_sleep_time = randint(3,6)
                            # logging.info('New order will be checked after %s',random_sleep_time)
                            # time.sleep(random_sleep_time)
                        else:
                            logging.info(availbleorders)
                        start_time,end_time = int(client_data['random_sleep_time'].split(',')[0]),int(client_data['random_sleep_time'].split(',')[1])
                        random_sleep_time = randint(start_time,end_time)
                        logging.info('New order will be checked after %s',random_sleep_time)
                        time.sleep(random_sleep_time)
                    else:
                        try:
                            send_login_error_mail(portal_name,client_data) #function for sending login error
                            logging.info('Making Client Inactive in DB')
                            cursorexec("order_acceptance","UPDATE",f"UPDATE `ca` SET `Status`='Inactive' , `comments`='Login Failed' WHERE userid = '{client_data['userid']}' LIMIT 1")

                        except Exception as ex:
                            init.exception_mail_send(portal_name,portal_name,ex)
                            logging.info(ex)
                else:
                    logging.info('Client Inactive..Waiting 30 minutes before checking DB')
                    inactive_inDB(client_data['Client_name'],portal_name)
        
        except Exception as ex:
            #reconnect and continue loop from beginning
            time.sleep(30)
            exception_mail_send(portal_name,portal_name,ex)
            logging.info(ex)
            #cursor=get_cursor("order_acceptance").reconnect(attempts=2, delay=1)
            continue
if __name__ == "__main__":
    main()
