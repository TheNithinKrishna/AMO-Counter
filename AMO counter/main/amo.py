"""FILE CONTAINS THE AMO MAIN FUNCTION which is used to run the acceptance"""
import ctypes
from helper.amo import Amo
from stdlib.utility import cursorexec,write_to_db,ignored_order,send_login_error_mail,inactive_inDB,client_mail_send,send_accepted_mail,logger_portal,zipcode_check,successmessageconditionalyaccept,check_counter_accepted
import logging
import time
import sender
from datetime import datetime
from random import randint
import sys

userid = "148209"
portal_name="AMO"
# userid = sys.argv[1]
# portal_name=sys.argv[2]


def main():
    isLoggedIn = False
    init=Amo("")
    count=0
    while True:
        try:
            accepted = []
            ignored = []  
            countered=[]
            client_data = cursorexec("order_acceptance","SELECT",f"""SELECT * FROM `AMO` WHERE  `userid` = '{userid}' LIMIT 1""")    
            init.client_data=client_data  
            if count == 0:  
                logger_portal(client_data['Client_name'],portal_name)    
                count+=1
            ctypes.windll.kernel32.SetConsoleTitleW(f"{client_data['Client_name']}-Amo")
            logging.info(
                "AMO acceptor for {}".format(client_data['Client_name']))
            cursorexec("order_updation",'UPDATE',f"""UPDATE `servercheck` SET
                           `event`='{datetime.now()}' where `userid`='{userid}' """)
                            
            if (client_data['Status'] == "Active"):
                
                isLoggedIn,session = init.login(isLoggedIn,userid,client_data['Client_name'],portal_name) # This function is used to login into the amo portal           
                if isLoggedIn:
                    orderFlag,availableorders,session,accept_token=init.check_orders(session,portal_name) #check Orders available in the amo portal
                    if orderFlag: 
                        common_db_data=cursorexec("order_updation",'SELECT',"""SELECT * FROM `common_data_acceptance` """)                        
                        for avail_order in availableorders:
                            order_received_time=datetime.now()
                            address = avail_order['SubjectPropertyAddress1']+' '+avail_order['SubjectPropertyAddress2']+', '+avail_order['SubjectPropertyCity']+', '+avail_order['SubjectPropertyState']+' '+avail_order['SubjectPropertyPostalCode']
                            to_accept,due_date,fee_portal,session,criteriaflag = init.criteria_check(avail_order,session,portal_name) # check criteria satisfying for available orders                          
                            if criteriaflag:
                                acceptFlag,due_date,address=init.accept_orders(to_accept,session,accept_token,portal_name)    #Accept orders that criteria are satisfied                            
                                if acceptFlag:                                    
                                    accepted.append({"due_date":due_date, "fee_portal":fee_portal, "Address":address,"Ordertype":to_accept['VendorProduct'],"OrderId":to_accept['OrderID'],'Zipcode':to_accept['SubjectPropertyPostalCode'],"order_received_time":order_received_time})                                    
                                else:
                                    ignored.append({'to_accept':to_accept,'ignoredmsg':'Order Expired','Address':address,'fee_portal':fee_portal,"session":session,'client_data':client_data,'Zipcode':to_accept['SubjectPropertyPostalCode'],"order_received_time":order_received_time})
                                    logging.info("Order Not accepted,Response change while accepting order {}".format(client_data['Client_name']))
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
                            subject='Amo order Accepted!'                         
                            mail_status=send_accepted_mail(accept['due_date'], accept['fee_portal'],accept['Ordertype'], accept['Address'],accept['OrderId'],client_data['from_mail'],client_data['to_clientMail'],client_data['to_ecesisMail'],client_data['Client_name'],subject,portal_name)
                            time.sleep(5)
                            counter_accepted_flag = check_counter_accepted(client_data,accept['Address'],portal_name)
                            if not counter_accepted_flag:
                                write_to_db(client_data,str(datetime.now()),accept['due_date'],'amo',fee_portal,accept['Ordertype'],accept["Address"],mail_status,portal_name,accept['OrderId'],subject,accept['order_received_time'])
                        
                        for avail_order in countered:
                            try:                                
                                subject='Fee Requested!! - AMO'
                                logging.info('Fee Requested!! - AMO {}'.format(avail_order['address']))
                                mail = sender.Mail('smtp.gmail.com', client_data['from_mail'], "$oft@ece2021", 465, use_ssl=True,fromaddr=client_data['from_mail']) 
                                mail_message_body=successmessageconditionalyaccept(client_data['Client_name'],str(datetime.now()), avail_order['due_date'], "amo", avail_order['fee_portal'], avail_order['order_type'], avail_order['address'],avail_order['order_id'],requested_fee,"Fee Requested")
                                client_mail_send(mail,client_data['to_clientMail'],client_data['to_ecesisMail'],subject,mail_message_body)
                                mail_status='Countered'
                                logging.info('Countered')
                                write_to_db(client_data,str(datetime.now()),avail_order['due_date'],'amo',fee_portal,avail_order['order_type'],avail_order['address'],mail_status,portal_name,avail_order['order_id'],subject,avail_order['order_received_time'])
                            except Exception as ex:
                                print(ex)
                                mail_status='Countered'
                                write_to_db(client_data,str(datetime.now()),avail_order['due_date'],'amo',fee_portal,avail_order['order_type'],avail_order['address'],mail_status,portal_name,avail_order['order_id'],subject,avail_order['order_received_time'])
                                logging.info('Exception Here: {}'.format(ex))
                        for ignored in ignored:
                            subject=f"Ignored Order!!! - Amo-{ignored['ignoredmsg']}"
                            order_details=ignored['to_accept']                            
                            ignored_order(ignored['Address'],order_details['VendorProduct'],ignored['ignoredmsg'],ignored['fee_portal'],ignored['client_data'],portal_name,ignored['Zipcode'],subject,ignored['order_received_time'])
                    else:
                        logging.info(" No New Orders Available in portal ")                    
                else:
                    send_login_error_mail(portal_name,client_data)
                    logging.info('Making Client Inactive in DB')
                    cursorexec("order_acceptance","UPDATE",f"UPDATE `{portal_name}` SET `Status`='Inactive' , `comments`='Login Error' WHERE userid = '{client_data['userid']}' LIMIT 1")

            else:
                logging.info("Client in Inactive {}".format(client_data['Client_name']))
                inactive_inDB(client_data['Client_name'],portal_name)
                time.sleep(1800)#wait for 30 minutes and continue loop
            # logging.info(client_data['Client_name'])
            # random_sleep_time = randint(60, 90)
            # logging.info('New order will be checked after %s' %
            #             (random_sleep_time))
            # time.sleep(random_sleep_time)
            start_time,end_time = int(client_data['random_sleep_time'].split(',')[0]),int(client_data['random_sleep_time'].split(',')[1])
            random_sleep_time = randint(start_time,end_time)
            logging.info('New order will be checked after %s',random_sleep_time)
            time.sleep(random_sleep_time)
            
        except Exception as ex:
            # reconnect and continue loop from beginning
            logging.info("ERROR : {}".format(ex),client_data['Client_name'])
            time.sleep(randint(60, 90))
            isLoggedIn = False
            continue
            
if __name__ == '__main__':
    main()
