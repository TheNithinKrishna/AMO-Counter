import json
import time
import datetime
from xml.etree import ElementTree
import os
import logging
import requests
import sender
import mysql.connector
# from geocodeus import ZipCache
from stdlib.creds import dbcred,email_cred
import imaplib
import sys
from datetime import date
from datetime import timedelta
# import pgeocode


# cache = ZipCache()
today = datetime.datetime.now()
email_creds=email_cred()

# #Velocity check with cache
# CACHE_FILE = "cache.json"
# if not os.path.isfile(CACHE_FILE):
#     with open('cache.json', 'w') as f:
#         print("The cache file is created")
# MAX_CACHE_AGE = 1800  # Maximum age of cached data in seconds (30 minutes)

def login_into_gmail(imap_user, imap_password):
    conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    try:
        (retcode, capabilities) = conn.login(imap_user, imap_password)
    except:
        logging.info('Exception : {}'.format(sys.exc_info()[1]))
        conn.close()
        sys.exit(1)
    return conn

def check_ordertype(ordertype,orderfee,common_db_data,client_data,portal_name):
    try:
        ordertype=ordertype.strip()
        
        if ',' in ordertype:
            ordertype = ordertype.replace(',  ',' ').replace(', ',' ').replace(',',' ')
            logging.info(f'order type after removing comma is : {ordertype}')
    
        client_ordertype = client_data['Order_type'].strip()
        exterior_ordertypes=common_db_data['exterior_ordertypes'].split(',')
        interior_ordertypes=common_db_data['interior_ordertypes'].split(',')
        donot_accept_ordertypes=client_data['donot_accept_ordertypes'].split(',')        
        exterior_inspection_ordertypes=common_db_data['exterior_inspection_ordertypes'].split(',')
        exterior_commercial_ordertypes=common_db_data['exterior_commercial_ordertypes'].split(',')
        interior_inspection_ordertypes=common_db_data['interior_inspection_ordertypes'].split(',')
        interior_commercial_ordertypes=common_db_data['interior_commercial_ordertypes'].split(',')
        if ((ordertype.lower() in [x.lower() for x in exterior_ordertypes]) and ('Exterior' in client_ordertype)) and (ordertype.lower() not in [x.lower() for x in donot_accept_ordertypes]):
            return client_data['Price_min_ext'],client_data['Zipcode'],True
        elif ((ordertype.lower() in [x.lower() for x in exterior_inspection_ordertypes]) and ('Exterior Inspection' in client_ordertype)) and (ordertype.lower() not in [x.lower() for x in donot_accept_ordertypes]):
            return client_data['min_price_insp'],client_data['Zipcode'],True
        elif ((ordertype.lower() in [x.lower() for x in exterior_commercial_ordertypes]) and ('Exterior Commercial' in client_ordertype)) and (ordertype.lower() not in [x.lower() for x in donot_accept_ordertypes]):
            return client_data['Price_min_ext_comm'],client_data['Zipcode'],True
        elif ((ordertype.lower() in [x.lower() for x in interior_ordertypes]) and ('Interior' in client_ordertype)) and (ordertype.lower() not in [x.lower() for x in donot_accept_ordertypes]):
            return client_data['Price_min_int'],client_data['Int_Zipcode'],True
        elif ((ordertype.lower() in [x.lower() for x in interior_inspection_ordertypes]) and ('Interior Inspection' in client_ordertype)) and (ordertype.lower() not in [x.lower() for x in donot_accept_ordertypes]):
            return client_data['min_price_int_insp'],client_data['Int_Zipcode'],True
        elif ((ordertype.lower() in [x.lower() for x in interior_commercial_ordertypes]) and ('Interior Commercial' in client_ordertype)) and (ordertype.lower() not in [x.lower() for x in donot_accept_ordertypes]):
            return client_data['Price_min_int_comm'],client_data['Zipcode'],True
        else:
            return orderfee,ordertype,False
    except Exception as ex:
        logging.info(ex)
        exception_mail_send(portal_name,client_data['Client_name'],ex)
        

def check_decline_ordertype(ordertype,common_db_data,client_data,portal_name):
    try:
        ordertype=ordertype.strip()
        decline_ordertypes=client_data['decline_ordertypes'].split(',')
        exterior_ordertypes=common_db_data['exterior_ordertypes'].split(',')
        interior_ordertypes=common_db_data['interior_ordertypes'].split(',')
        exterior_inspection_ordertypes=common_db_data['exterior_inspection_ordertypes'].split(',')
        interior_inspection_ordertypes=common_db_data['interior_inspection_ordertypes'].split(',')
        if (ordertype.lower() in [x.lower() for x in exterior_ordertypes]) and ('exterior' in [x.lower() for x in decline_ordertypes]):
            return True
        elif (ordertype.lower() in [x.lower() for x in exterior_inspection_ordertypes]) and ('exterior inspection' in [x.lower() for x in decline_ordertypes]):
            return True
        elif (ordertype.lower() in [x.lower() for x in interior_ordertypes]) and ('interior' in [x.lower() for x in decline_ordertypes]):
            return True
        elif (ordertype.lower() in [x.lower() for x in interior_inspection_ordertypes]) and ('interior inspection' in [x.lower() for x in decline_ordertypes]):
            return True
        else:
            return False
    except Exception as ex:
        exception_mail_send(portal_name,client_data['Client_name'],ex)
        logging.info(ex)

def criteria_with_params(pricedb,zipcodedb, fee_portal, due_difference, zipcode, client_data,due,common_db_data,portal_name):
    try:
        if not client_data['due_difference']:client_data['due_difference']= 0
        logging.info('criteria_with_params')
        if float(fee_portal) >= pricedb:
            logging.info('{} price satisfied'.format(fee_portal))
            if zipcodedb.get(str(zipcode),None) is not None :          #Convert to dictionary
                if client_data['Client_name'] not in common_db_data['velocityClients_within_coverage']:
                    logging.info("Zipcode satisfied")
                    if int(due_difference) > int(client_data['due_difference']):
                        logging.info("Due Date Satisfied")
                        flag=True
                        return due,fee_portal,flag
                    else:
                        logging.info('Due Date Not Satisfied')
                        ignored_msg = "Due Date Not Satisfied"
                        flag=False
                        return ignored_msg,fee_portal,flag
                else:
                    reps = velocity_check(zipcode,20,client_data['Client_name'],portal_name)
                    if reps >= 2:
                        logging.info(f"Zipcode satisfied while checking velocity, Reps: {reps}")
                        if int(due_difference) > int(client_data['due_difference']):
                            flag=True
                            return due,fee_portal,flag
                        else:
                            logging.info('Due Date Not Satisfied')
                            ignored_msg = "Due Date Not Satisfied"
                            flag=False
                            return ignored_msg,fee_portal,flag
                    else:
                        logging.info("Rep not available")
                        ignored_msg = "Zipcode Not satisfied"
                        flag=False
                        return ignored_msg,fee_portal,flag
            else:
                if client_data['Client_name'] in common_db_data['velocityClients']:
                    reps = velocity_check(zipcode,20,client_data['Client_name'],portal_name)
                    if common_db_data['bangnotavailablezip'] is not None:
                    # if client_data['NotavailableZip'] is not None:S
                        if zipcode not in common_db_data['bangnotavailablezip']:
                        # if zipcode not in client_data['NotavailableZip']:
                            if reps >= 2:
                                logging.info("Zipcode satisfied while checking velocity")
                                if int(due_difference) > int(client_data['due_difference']):
                                    flag=True
                                    return due,fee_portal,flag
                                else:
                                    logging.info('Due Date Not Satisfied')
                                    ignored_msg = "Due Date Not Satisfied"
                                    flag=False
                                    return ignored_msg,fee_portal,flag
                            else:
                                logging.info("Rep not available")
                                ignored_msg = "Zipcode Not satisfied"
                                flag=False
                                return ignored_msg,fee_portal,flag
                        else:
                            ignored_msg = "Zipcode Not satisfied"
                            logging.info("Zipcode Not satisfied")
                            flag=False
                            return ignored_msg,fee_portal,flag
                    else:
                        ignored_msg = "Zipcode Not satisfied"
                        logging.info("Zipcode Not satisfied")
                        flag=False
                        return ignored_msg,fee_portal,flag
                else:
                    ignored_msg = "Zipcode Not satisfied"
                    logging.info("Zipcode Not satisfied")
                    flag=False
                    return ignored_msg,fee_portal,flag
        else:
            if int(due_difference) > int(client_data['due_difference']):
                logging.info("Due Date Satisfied")
                ignored_msg = f"Order price Not satisfied"
                logging.info(f"Order price Not satisfied -${fee_portal}")
                flag=False
                return ignored_msg,fee_portal,flag
            else:
                logging.info('Due Date Not Satisfied')
                ignored_msg = "Due Date Not Satisfied"
                flag=False
                return ignored_msg,fee_portal,flag
    except Exception as ex:
        exception_mail_send(portal_name,client_data['Client_name'],ex)
        logging.info(ex)



# def load_cache():
#     """This function loads the cache"""
#     try:
#         with open(CACHE_FILE, "r") as file:
#             return json.load(file)
#     except (FileNotFoundError, json.JSONDecodeError,json.decoder.JSONDecodeError):
#         return {}

# def save_cache(cache):
#     """This function writes to a cache.json which stores the velocity results"""
#     with open(CACHE_FILE, "w") as file:
#         json.dump(cache, file)

# def get_cached_result(zip_code, miles, numogpgrhrs):
#     """This function returns the velocity result from cache.json file"""
#     cache = load_cache()
#     key = f"{zip_code}_{miles}_{numogpgrhrs}"
#     if key in cache:
#         data, timestamp = cache[key]
#         current_time = time.time()
#         if current_time - timestamp <= MAX_CACHE_AGE:
#             print("Retrieving result from cache.")
#             return data
#         else:
#             del cache[key]  # Remove expired data from cache
#             save_cache(cache)
#     return None

# def cache_result(zip_code, miles, numogpgrhrs, result):
#     """This function caches the velocity result to cache.json file"""
#     cache = load_cache()
#     key = f"{zip_code}_{miles}_{numogpgrhrs}"
#     cache[key] = (result, time.time())
#     save_cache(cache)
#     print("Result cached.")

def check_counter_accepted(client_data,address,portal,due_date):
    try:
        today = date.today()
        date_time = today.strftime('%Y-%m-%d')
        today_date=date_time+' 23:59:00'
        yesterday = today - timedelta(days=1)
        yesdate_time = yesterday.strftime('%Y-%m-%d')
        yesterday_date=yesdate_time+' 00:00:00'

        print(today_date)
        print(yesterday_date)
        logging.info('Connected to MySQL database...')
        
        data=cursorexec("order_updation","SELECT","SELECT * FROM `mainstreetaccepted` WHERE `ClientName` = '{}' and `Address` = '{}' AND AcceptedTime BETWEEN '{}' AND '{}' AND MailStatus = 'Countered'".format(client_data['Client_name'],address,yesterday_date,today_date))
    
        if data:
            counter_accepted_flag = True
            logging.info(f'Countered Order Accepted for Address: {address}')
            # cursorexec("order_updation","UPDATE","UPDATE `mainstreetaccepted` SET `MailStatus` = 'Countered Order Accepted' WHERE `ClientName` = '{}' AND `ProviderName` = '{}' and `Address` = '{}'".format(client_data['Client_name'],portal,address))
            cursorexec("order_updation","UPDATE","UPDATE `mainstreetaccepted` SET `DueDate` = '{}', `MailStatus` = 'Countered Order Accepted' WHERE `ClientName` = '{}' AND `ProviderName` = '{}' and `Address` = '{}'".format(due_date,client_data['Client_name'],portal,address))    
        else:
            counter_accepted_flag = False
            logging.info(f'Not a Countered Order for Address: {address}')
        return counter_accepted_flag
    except Exception as ex:
        logging.info(f"Exception in check_counter_accepted: {ex}")
        exception_mail_send(portal,client_data['Client_name'],ex)

def velocity_check(zip_code, miles,client_name,portal):
    """This function is used to check whether reps are available in Velocity"""
    max_retries = 2
    retry_delay = 0
    attempt = 0
    while attempt < max_retries:
        try:
            cnx = mysql.connector.connect(user="order", password="acceptance", host="34.70.96.52", database="order_updation",autocommit=True)
            cursor = cnx.cursor(buffered=True, dictionary=True)
            cursor.execute(f"""SELECT * FROM `google_geolocation_data` WHERE zipcode={zip_code} """)
            data=cursor.fetchone()
            if data!=None:
                logging.info("Geo Location already available in database")
                lat=data['latitude']
                lng=data['longitude']
            else:
                session1=requests.session()
                api_key="AIzaSyBai-oUJPePJD6jIaiI8xO36F3AytcPwGY"
                url=f"https://maps.googleapis.com/maps/api/geocode/json?key={api_key}&components=postal_code:{zip_code}"
                response=session1.get(url)
                if json.loads(response.content)['status'] != 'ZERO_RESULTS':
                    lat=json.loads(response.content)['results'][0]['geometry']['location']['lat']
                    lng=json.loads(response.content)['results'][0]['geometry']['location']['lng']
                    logging.info(f'Lat: {lat}, Lan: {lng}')
                    cursor.execute(f"INSERT INTO `google_geolocation_data` (`zipcode`,`latitude`,`longitude`) VALUES ('{zip_code}','{lat}','{lng}') ")
                else:
                    logging.info("Lat and long cound not be fetched")
                    return 0
            cursor.close()
            session=requests.session()
            response=session.get('https://bpophotoflow.com/coverage_markers.php?lat={}&lng={}&radius={}'.format(lat,lng,miles))
            phtghr_count=0
            for child in ElementTree.fromstring(response.content).iter('marker'):
                if child.attrib['color'] == 'blue.png':
                    phtghr_count=phtghr_count+1
                #print(phtghr_count,zips)
            logging.info(f"phtghr_count: {phtghr_count} , zip_code:{zip_code}")
            return phtghr_count
        except Exception as ex:
                logging.info(f"Exception in velocityCheck: {ex}")
                attempt += 1
                if attempt < max_retries:
                    logging.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:    
                    try:
                        from sender import Mail  # Ensure sender is correctly imported
                        mail = sender.Mail('smtp.gmail.com', "loginerrornotifier@gmail.com" , "eqkmgbkfbopdkfpw", 465, use_ssl=True,
                                                fromaddr="loginerrornotifier@gmail.com")
                        logging.info('Connected to email')
                        err_message = f"""This is an automatic notification:
                        Issue In checking velocity for {client_name}'s {portal} account"""
                        logging.info(err_message)
                        mail.send_message(subject=f'Velocity check Issue', to="teamsoftware@ecesistech.com", body=err_message)
                        return 0
                    except Exception as e:
                        logging.error(f"Exception in sending error notification: {e}")
                        return 0

def write_to_db(client_data,time_now,duedate,provider_name,order_fee,ordertype,order_address,mail_status,portal,order_id,subjectline,order_received_time):
    """This function writes the accepted order details to mainstreetaccepted database"""
    try:
        logging.info("Updating accepted order details to DB ...")
        order_zipcode = str(order_address).split(" ")[-1]
        if '-' in order_zipcode:order_zipcode = order_zipcode.split("-")[0]
        
        if client_data['from_mail'] == 'notificationalert@bpoacceptor.com' or client_data['from_mail'] == 'bangrealty@bpoacceptor.com' or client_data['from_mail'] == 'keystoneholding@bpoacceptor.com' or client_data['from_mail'] == 'notifications@bpoacceptor.com' or client_data['from_mail'] == 'info@bpoacceptor.com':
            
            from_mail_id = client_data['from_mail']
            logging.info(f"from mail : {from_mail_id}")
            cursorexec("order_updation","INSERT",f"""INSERT INTO `mainstreetaccepted`(`ClientName`, `AcceptedTime`, `DueDate`, `ProviderName`, `OrderFee`, `Order Type`, `Address`, `to_ecesisMail`, `to_clientMail`, `from_mail`, `fromaddresspwd`, `MailStatus`,`order_id`,`subjectline`,`order_zipcode`,`order_received_time`,`client_type`)
                        VALUES ('{client_data['Client_name']}','{time_now}','{duedate}','{provider_name}','{order_fee}','{ordertype}','{order_address}','{client_data['to_ecesisMail']}','{client_data['to_clientMail']}','{client_data['from_mail']}','{email_creds[from_mail_id]}','{mail_status}','{order_id}','{subjectline}','{order_zipcode}','{order_received_time}','{client_data['client_type']}')""")
        
        else:
            logging.info(f"from mail from client data: {client_data['from_mail']}")
            from_mail_id = 'info@bpoacceptor.com'
            cursorexec("order_updation","INSERT",f"""INSERT INTO `mainstreetaccepted`(`ClientName`, `AcceptedTime`, `DueDate`, `ProviderName`, `OrderFee`, `Order Type`, `Address`, `to_ecesisMail`, `to_clientMail`, `from_mail`, `fromaddresspwd`, `MailStatus`,`order_id`,`subjectline`,`order_zipcode`,`order_received_time`,`client_type`)
                        VALUES ('{client_data['Client_name']}','{time_now}','{duedate}','{provider_name}','{order_fee}','{ordertype}','{order_address}','{client_data['to_ecesisMail']}','{client_data['to_clientMail']}','{from_mail_id}','{email_creds[from_mail_id]}','{mail_status}','{order_id}','{subjectline}','{order_zipcode}','{order_received_time}','{client_data['client_type']}')""")

    except Exception as ex:
        logging.info('Exception arrises : %s',ex)
        exception_mail_send(portal,client_data['Client_name'],ex)

def get_cursor(db):
    """This function Connects to the database"""
    cred=dbcred()
    cnx = mysql.connector.connect(user=cred['DB_user'], password=cred['DB_password'], host=cred['DB_host'], database=db,
                                  autocommit=True)
    cursor = cnx.cursor(buffered=True, dictionary=True)
    return cnx, cursor

def send_accepted_mail(due_date, order_fee,ordertype,order_address,order_id,fromaddress,to_client_mail,to_ecesis_mail,client_name,subject,portal):
    """This function is to send Order accepted Emails"""
    try:
        mail_status='Order Accepted'
        logging.info('Connected to email')
        
        if fromaddress == 'notificationalert@bpoacceptor.com' or fromaddress == 'bangrealty@bpoacceptor.com' or fromaddress == 'keystoneholding@bpoacceptor.com' or fromaddress == 'notifications@bpoacceptor.com' or fromaddress == 'info@bpoacceptor.com':
            logging.info(f"from mail : {fromaddress}")
            mail = sender.Mail('smtp.gmail.com', fromaddress , email_creds[fromaddress], 465, use_ssl=True,fromaddr=fromaddress)
       
        else:
            logging.info(f"from mail : {fromaddress}")
            fromaddress = 'info@bpoacceptor.com'
            mail = sender.Mail('smtp.gmail.com', fromaddress , email_creds[fromaddress], 465, use_ssl=True,fromaddr=fromaddress)
            
    
        success_message = successmessage(client_name,str(datetime.datetime.now()), due_date ,portal, order_fee, ordertype,order_address,order_id)
        client_mail_send(mail,to_client_mail,to_ecesis_mail,subject,success_message)
        
    except Exception as ex:
        mail_status='Accepted Mail Failure'
        exception_mail_send(portal,client_name,ex)
        logging.info('Exception arrises while sending mail')
        logging.info('Mail Not Send')
    return mail_status

def successmessage(client_name, acceptedtime, due_date, providename, orderfee, ordertype, address,order_id):
    """This Function returns the order accepted message template"""
    SUCCESS_MESSAGE = f"""This is an automatic notification that one of your orders was auto-accepted using our service:

    Client Name: {client_name}
    Accepted Time: {acceptedtime}
    Due Date: {due_date}
    Provider Name: {providename}
    Order Fee: {orderfee}
    Order Type: {ordertype}
    Address: {address}
    OrderID: {order_id}
    """
    return SUCCESS_MESSAGE


def successmessageconditionalyaccept(client_name, acceptedtime, due_date, providename, orderfee, ordertype, address,order_id,requested_fee,msg):
    """This Function returns the order conditionally accepted message template"""
    SUCCESS_MESSAGE = f"""This is an automatic notification that one of your orders was {msg} using our service:

    Client Name: {client_name}
    Accepted Time: {acceptedtime}
    Due Date: {due_date}
    Provider Name: {providename}
    Order Fee: {orderfee}
    Order Type: {ordertype}
    Address: {address}
    OrderID: {order_id}
    Requested Fee: {requested_fee}
    """
    return SUCCESS_MESSAGE

def successmessageconditionalyaccept2(client_name, acceptedtime, due_date, providename, orderfee, ordertype, address,order_id,requested_due,msg):
    """This Function returns the order conditionally accepted message template"""
    SUCCESS_MESSAGE = f"""This is an automatic notification that one of your orders was {msg} using our service:

    Client Name: {client_name}
    Accepted Time: {acceptedtime}
    Due Date: {due_date}
    Provider Name: {providename}
    Order Fee: {orderfee}
    Order Type: {ordertype}
    Address: {address}
    OrderID: {order_id}
    Requested Due: {requested_due}
    """
    return SUCCESS_MESSAGE

def ignored_message(msg,address,ignored_msg,client_name,ordertype,fee,zipcode):
    """This Function contains the ignored order message"""
    ignored_message = f"""This is an automatic notification:
    {msg} order {address} since {ignored_msg}.
    Order details:
                Client Name - {client_name}
                Order type - {ordertype}
                Order Fee - {fee}
                Zipcode - {zipcode}"""
    return ignored_message

def client_mail_send(mail,to_client_mail,to_ecesis_mail,subject,success_message):
    """This Fucntion is used send mail notification to client"""
    if to_client_mail and to_ecesis_mail:
        # mail.send_message(subject=subject, to=('teamsoftware@ecesistech.com'),body=success_message)
        mail.send_message(subject=subject, to=(to_client_mail,to_ecesis_mail), body=success_message, bcc=(email_creds['exception_ecesis']))
    elif to_ecesis_mail:
        # mail.send_message(subject=subject, to=('teamsoftware@ecesistech.com'),body=success_message)
        mail.send_message(subject=subject, to=(to_ecesis_mail), body=success_message, bcc=(email_creds['exception_ecesis']))
    elif to_client_mail:
        # mail.send_message(subject=subject, to=('teamsoftware@ecesistech.com'),body=success_message)
        mail.send_message(subject=subject, to=(to_client_mail), body=success_message, bcc=(email_creds['exception_ecesis']))
    logging.info('Mail sent')


def close_cursor_connection(cursor, cnx):
    """This Fucntion is used to Close SQL Connection"""
    cursor.close()
    cnx.close()


def cursorexec(db,qtype,query):
    """This Fucntion is used to Execute SQL query"""
    cnx, cursor = get_cursor(db)
    cursor.execute(query)
    if "SELECT" in qtype:
        data = cursor.fetchone()
    else:
        data = "DATA INSERTED OR UPDATED SUCCESSFULLY"
    close_cursor_connection(cursor, cnx)
    return data

def logger_portal(client_name,portalname):
    """This Function is used to Setup logging"""
    path=f"BACKUP//{portalname}//{client_name}//" #Check path exist
    if not os.path.exists(path):os.makedirs(path)
    LOG_FILENAME = path + '{}'.format(client_name,) + today.strftime('%d-%m-%Y-%H-%M-%S.log')
    logging.basicConfig(filename=LOG_FILENAME, level=logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)
    logging.getLogger().propagate=False

def logger_mail(portal_name):
    try:
        path = f"BACKUP//{portal_name}//"  
        os.makedirs(path, exist_ok=True)  # Create path if it doesn't exist
        
        LOG_FILENAME = f"{path}{portal_name}-{today:%d-%m-%Y-%H-%M-%S}.log"
        
        logging.basicConfig(
            level=logging.INFO, 
            filename=LOG_FILENAME,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(console_handler)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)
        logging.getLogger().propagate=False
    except Exception as ex:
        print(ex)
          
def capacity_mail_send(client_name,portalname):
    """This Function is used to send Capacity Exceeded Mail"""
    currenttime=datetime.datetime.now()
    notification_message = 'This is an automatic notification that we are unable to accept orders for {} since capacity has exceeded'.format(client_name)
    try:
        data=cursorexec("order_updation","SELECT","SELECT COUNT(*) FROM `capacity_exceed` WHERE `ClientName` = '{}' and `Portal` = '{}'".format(client_name,portalname))
        if(data['COUNT(*)']==0):
            cursorexec("order_updation","INSERT","INSERT INTO `capacity_exceed` (`ClientName`,`Portal`,`UpdatedTime`) VALUES ('{}','{}','{}')".format(client_name,portalname,currenttime))
            mail = sender.Mail('smtp.gmail.com', email_creds['internal_notifier_email'] , email_creds['internal_notifier_password'], 465, use_ssl=True,fromaddr=email_creds['internal_notifier_email'])
            logging.info('Connected to email')
            logging.info(notification_message)
            if 'Bang' in client_name:
                mail.send_message(subject=f'{portalname} - Capacity Exceeded!!!!!!', to=(email_creds['capacity_mail'],email_creds['capacity_mail_sent'],email_creds['internal_email_notification'],'tvmcommunicationteam@gmail.com'), body=notification_message)
                logging.info('capacity Order Mail sent')
            else:    
                mail.send_message(subject=f'{portalname} - Capacity Exceeded!!!!!!', to=(email_creds['internal_email_notification'],'tvmcommunicationteam@gmail.com'), body=notification_message)
                logging.info('capacity Order Mail sent')
        else:
            data=cursorexec("order_updation","SELECT","SELECT * FROM `capacity_exceed` WHERE `ClientName` = '{}' and `Portal` = '{}'".format(client_name,portalname))
            time_in_db = data['UpdatedTime']
            logging.info('Time in DB %s ',time_in_db)
            currenttime = datetime.datetime.strptime(str(currenttime), '%Y-%m-%d %H:%M:%S.%f')
            time_in_db = datetime.datetime.strptime(str(time_in_db), '%Y-%m-%d %H:%M:%S.%f')
            duration = (currenttime - time_in_db).total_seconds() / 3600
            if duration >= 12:
                cursorexec("order_updation","UPDATE","UPDATE `capacity_exceed` SET `UpdatedTime` = '{}' WHERE `ClientName` = '{}' AND `Portal` = '{}'".format(currenttime,client_name,portalname))
                mail = sender.Mail('smtp.gmail.com', email_creds['internal_notifier_email'] , email_creds['internal_notifier_password'], 465, use_ssl=True,fromaddr=email_creds['internal_notifier_email'])
                if 'Bang' in client_name:
                    mail.send_message(subject=f'{portalname} - Capacity Exceeded!!!!!!', to=(email_creds['capacity_mail'],email_creds['capacity_mail_sent'],email_creds['internal_email_notification'],'tvmcommunicationteam@gmail.com'), body=notification_message)
                    logging.info('capacity Order Mail sent')
                else:                
                    mail.send_message(subject=f'{portalname} - Capacity Exceeded!!!!!!', to=(email_creds['internal_email_notification'],'tvmcommunicationteam@gmail.com'), body=notification_message)
                    logging.info('capacity Order Mail sent')
    except Exception as ex:
        exception_mail_send(portalname,client_name,ex)
        logging.info(ex)


def exception_mail_send(portal_name,client_name,ex):
    """This Function is used to send Exception  Mails"""
    try:
        mail = sender.Mail('smtp.gmail.com', email_creds['exception_email'] , email_creds['exception_password'], 465, use_ssl=True,fromaddr=email_creds['exception_email'])
        logging.info('Connected to email')
        err_message = """This is an automatic notification:
Exception in {}'s {} account.

Exception in {}
""".format(client_name,portal_name,ex)
        logging.info(err_message)

        mail.send_message(subject=f'{portal_name} Exception!', to=email_creds['exception_email'], body=err_message)
        logging.info('Exception Mail sent')
    except Exception as ec:
        logging.info(ec)
        
def checkIsAccepted(client_data, address, portal):
    try:
        today = date.today()
        date_time = today.strftime('%Y-%m-%d')
        today_date=date_time+' 23:59:00'

        yesterday = today - timedelta(days=1)
        yesdate_time = yesterday.strftime('%Y-%m-%d')
        yesterday_date=yesdate_time+' 00:00:00'

        print(today_date)
        print(yesterday_date)
        logging.info('Connected to MySQL database...')
        
        data=cursorexec("order_updation", "SELECT", "SELECT `ClientName`, `ProviderName`, `address` FROM `mainstreetaccepted` WHERE `ProviderName` = '{}' AND `Address` = '{}' AND AcceptedTime BETWEEN '{}' AND '{}' AND MailStatus = 'Order Accepted'".format(portal, address, yesterday_date, today_date))
        logging.info("Accepted order - {}".format(data))
        if data:
            accepted_flag = True
            logging.info('Order Accepted by the client {}'.format(data['ClientName']))
        else:
            accepted_flag = False
            logging.info(f'Not a Accepted Order - Address: {address}')
        return accepted_flag
    except Exception as ex:
        logging.info(f"Exception in checkIsAccepted: {ex}")
        exception_mail_send(portal,client_data['Client_name'],ex)

def ignored_order(address,ordertype,ignored_msg,fee_portal,clientData,portal,zipcode,subject,order_received_time):
    """This Function is used to Send Ignored order Emails"""
    logging.info(ignored_msg)
    common_db_data=cursorexec("order_updation",'SELECT',"""SELECT * FROM `common_data_acceptance` """)
    try:
        logging.info('Connected to MySQL database...')
        data=cursorexec("order_updation","SELECT","SELECT * FROM `Ignored_orders` WHERE `client_Name` = '{}' and `Address` = '{}' ORDER BY `timestamp` DESC limit 1".format(clientData['Client_name'],address))
        data1=cursorexec("order_updation","SELECT","SELECT * FROM `mainstreetaccepted` WHERE `ClientName` = '{}' and `Address` = '{}' and 'MailStatus' not like 'Countered' ORDER BY `AcceptedTime` DESC limit 1".format(clientData['Client_name'],address))
        def ignored_mail_send():
            logging.info("Send Ignore Mail...")
            process_completed_time = datetime.datetime.now()
            if ignored_msg == 'Order Expired':
                acceptedFlag = checkIsAccepted(clientData, address, portal)
                if acceptedFlag:
                    expireMessage = 'Orders Expired due to Accepted by Other Client'
                    logging.info("Orders accepted by other client")
                    cursorexec("order_updation","INSERT","INSERT INTO `Ignored_orders`(`client_Name`, `Address`, `Portal`,`ignored_reason`,`ordertype`,`orderfee`,`order_zipcode`,`order_received_time`,`process_completed_time`,`client_type`) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(clientData['Client_name'],address,portal,expireMessage,ordertype,fee_portal,zipcode,str(order_received_time),str(process_completed_time),clientData['client_type']))
                else:
                    cursorexec("order_updation","INSERT","INSERT INTO `Ignored_orders`(`client_Name`, `Address`, `Portal`,`ignored_reason`,`ordertype`,`orderfee`,`order_zipcode`,`order_received_time`,`process_completed_time`,`client_type`) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(clientData['Client_name'],address,portal,ignored_msg,ordertype,fee_portal,zipcode,str(order_received_time),str(process_completed_time),clientData['client_type']))
            else:
                cursorexec("order_updation","INSERT","INSERT INTO `Ignored_orders`(`client_Name`, `Address`, `Portal`,`ignored_reason`,`ordertype`,`orderfee`,`order_zipcode`,`order_received_time`,`process_completed_time`,`client_type`) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(clientData['Client_name'],address,portal,ignored_msg,ordertype,fee_portal,zipcode,str(order_received_time),str(process_completed_time),clientData['client_type']))
            if 'Bang' in clientData['Client_name']:
                mail = sender.Mail('smtp.gmail.com', email_creds['ignored_bang_mail'] , email_creds['ignored_bang_mail_password'], 465, use_ssl=True,fromaddr=email_creds['ignored_bang_mail'])
                logging.info('Connected to email')
                ignormsg=ignored_message("Unable to accept",address,ignored_msg,clientData['Client_name'],ordertype,fee_portal,zipcode)
                logging.info(ignormsg)
                if 'not satisfied' in ignored_msg.lower():
                    client_mail_send(mail,clientData['to_clientMail'],clientData['to_ecesisMail'],subject,ignormsg)
                    logging.info('Ignored Order Mail sent')
                else:
                    logging.info('No Need to Mail sent')
            else:    
                mail = sender.Mail('smtp.gmail.com', email_creds['ignored_mail'] , email_creds['ignored_psswd'], 465, use_ssl=True,fromaddr=email_creds['ignored_mail'])
                logging.info('Connected to email')
                ignormsg=ignored_message("Unable to accept",address,ignored_msg,clientData['Client_name'],ordertype,fee_portal,zipcode)
                logging.info(ignormsg)
                if 'not satisfied' in ignored_msg.lower():
                    if clientData['Client_name'] in common_db_data['ignored_order_mail_send_clients']:
                        client_mail_send(mail,clientData['to_clientMail'],clientData['to_ecesisMail'],subject,ignormsg)
                    else:
                        mail.send_message(subject, to=email_creds['exception_email'], body=ignormsg)
                    logging.info('Ignored Order Mail sent')
                else:
                    logging.info('No Need to Mail sent')

        if data1:
            acceptedtime = data1['AcceptedTime']
            time_gap = (today-acceptedtime).days
            if 0 <= int(time_gap)<= 2:
                logging.info("This address is already accepted for this client %s",address) 
            else:
                if data:
                    ignored_time = data['timestamp']
                    time_gap1 = (today-ignored_time).days
                    if int(time_gap1)>0:
                        ignored_mail_send()
                    else:
                        logging.info("Mail already send for %s",address)    
                else:
                    ignored_mail_send()       
        elif data:
            ignored_time = data['timestamp']
            time_gap = (today-ignored_time).days
            if int(time_gap)>0:
                ignored_mail_send()
            else:
                logging.info("Mail already send for %s",address)
        else:
            ignored_mail_send()
            logging.info('Ignored Order Mail sent')
    except Exception as ex:
        exception_mail_send(portal,clientData['Client_name'],ex)
        logging.info(ex)

def ignored_order_subjectline(address,ordertype,ignored_msg,fee_portal,clientData,portal,zipcode,subject,order_received_time,subjectline):
    """This Function is used to Send Ignored order Emails"""
    logging.info(ignored_msg)
    common_db_data=cursorexec("order_updation",'SELECT',"""SELECT * FROM `common_data_acceptance` """)
    try:
        logging.info('Connected to MySQL database...')
        data=cursorexec("order_updation","SELECT","SELECT * FROM `Ignored_orders` WHERE `client_Name` = '{}' and `Address` = '{}' ORDER BY `timestamp` DESC limit 1".format(clientData['Client_name'],address))
        data1=cursorexec("order_updation","SELECT","SELECT * FROM `mainstreetaccepted` WHERE `ClientName` = '{}' and `Address` = '{}' and 'MailStatus' not like 'Countered' ORDER BY `AcceptedTime` DESC limit 1".format(clientData['Client_name'],address))
        def ignored_mail_send():
            logging.info("Send Ignore Mail...")
            process_completed_time = datetime.datetime.now()
            if ignored_msg == 'Order Expired':
                acceptedFlag = checkIsAccepted(clientData, address, portal)
                if acceptedFlag:
                    expireMessage = 'Orders Expired due to Accepted by Other Client'
                    logging.info("Orders accepted by other client")
                    cursorexec("order_updation","INSERT","INSERT INTO `Ignored_orders`(`client_Name`, `Address`, `Portal`,`ignored_reason`,`ordertype`,`orderfee`,`order_zipcode`,`order_received_time`,`process_completed_time`,`client_type`,`subjectline`) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(clientData['Client_name'],address,portal,expireMessage,ordertype,fee_portal,zipcode,str(order_received_time),str(process_completed_time),clientData['client_type'],subjectline))
                else:
                    cursorexec("order_updation","INSERT","INSERT INTO `Ignored_orders`(`client_Name`, `Address`, `Portal`,`ignored_reason`,`ordertype`,`orderfee`,`order_zipcode`,`order_received_time`,`process_completed_time`,`client_type`,`subjectline`) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(clientData['Client_name'],address,portal,ignored_msg,ordertype,fee_portal,zipcode,str(order_received_time),str(process_completed_time),clientData['client_type'],subjectline))
            else:
                cursorexec("order_updation","INSERT","INSERT INTO `Ignored_orders`(`client_Name`, `Address`, `Portal`,`ignored_reason`,`ordertype`,`orderfee`,`order_zipcode`,`order_received_time`,`process_completed_time`,`client_type`,`subjectline`) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(clientData['Client_name'],address,portal,ignored_msg,ordertype,fee_portal,zipcode,str(order_received_time),str(process_completed_time),clientData['client_type'],subjectline))
            if 'Bang' in clientData['Client_name']:
                mail = sender.Mail('smtp.gmail.com', email_creds['ignored_bang_mail'] , email_creds['ignored_bang_mail_password'], 465, use_ssl=True,fromaddr=email_creds['ignored_bang_mail'])
                logging.info('Connected to email')
                ignormsg=ignored_message("Unable to accept",address,ignored_msg,clientData['Client_name'],ordertype,fee_portal,zipcode)
                logging.info(ignormsg)
                if 'not satisfied' in ignored_msg.lower():
                    client_mail_send(mail,clientData['to_clientMail'],clientData['to_ecesisMail'],subject,ignormsg)
                    logging.info('Ignored Order Mail sent')
                else:
                    logging.info('No Need to Mail sent')
            else:    
                mail = sender.Mail('smtp.gmail.com', email_creds['ignored_mail'] , email_creds['ignored_psswd'], 465, use_ssl=True,fromaddr=email_creds['ignored_mail'])
                logging.info('Connected to email')
                ignormsg=ignored_message("Unable to accept",address,ignored_msg,clientData['Client_name'],ordertype,fee_portal,zipcode)
                logging.info(ignormsg)
                if 'not satisfied' in ignored_msg.lower():
                    if clientData['Client_name'] in common_db_data['ignored_order_mail_send_clients']:
                        client_mail_send(mail,clientData['to_clientMail'],clientData['to_ecesisMail'],subject,ignormsg)
                    else:
                        mail.send_message(subject, to=email_creds['exception_email'], body=ignormsg)
                    logging.info('Ignored Order Mail sent')
                else:
                    logging.info('No Need to Mail sent')

        if data1:
            acceptedtime = data1['AcceptedTime']
            time_gap = (today-acceptedtime).days
            if 0 <= int(time_gap)<= 2:
                logging.info("This address is already accepted for this client %s",address) 
            else:
                if data:
                    ignored_time = data['timestamp']
                    time_gap1 = (today-ignored_time).days
                    if int(time_gap1)>0:
                        ignored_mail_send()
                    else:
                        logging.info("Mail already send for %s",address)    
                else:
                    ignored_mail_send()       
        elif data:
            ignored_time = data['timestamp']
            time_gap = (today-ignored_time).days
            if int(time_gap)>0:
                ignored_mail_send()
            else:
                logging.info("Mail already send for %s",address)
        else:
            ignored_mail_send()
            logging.info('Ignored Order Mail sent')
    except Exception as ex:
        exception_mail_send(portal,clientData['Client_name'],ex)
        logging.info(ex)

def inactive_inDB(client_name,portal):
    """This Function is used to Sent the inactive in database email """
    try:
        mail = sender.Mail('smtp.gmail.com', email_creds['internal_notifier_email'] , email_creds['internal_notifier_password'], 465, use_ssl=True,
                               fromaddr=email_creds['internal_notifier_email'])
        logging.info('Connected to email')
        err_message = f"""This is an automatic notification:
        The client is Inactive in Database for {client_name}'s {portal} account"""
        logging.info(err_message)
        mail.send_message(subject=f'{portal}:- Inactive In Database!', to=email_creds['internal_email_notification'], body=err_message)
        logging.info('Inactive Mail sent')
    except Exception as ex:
        exception_mail_send(portal,client_name,ex)
        logging.info(ex)



def checkip(client_ip):
    """This Function is used to check if the ip address is US and also to set the proxy"""
    try:
        session = requests.Session()
        proxies = {
            'http': f'http://{client_ip}',
            'https': f'http://{client_ip}'
            }
        
        session.proxies.update(proxies)
        ip_test_url1="https://www.google.com/"
        ipapify = session.get(ip_test_url1)
        if ipapify.status_code == 200:
            return True,session
        else:
            return False,session
    except Exception as ex:
        logging.info(f'Exception in Checkip function: {ex}')
        return False,session

def send_login_error_mail(portal_name,client_data):
    """This function is to send login error emails"""
    try:
        mail = sender.Mail('smtp.gmail.com', email_creds['login_error_email'] , email_creds['login_error_password'], 465, use_ssl=True,
                                   fromaddr=email_creds['login_error_email'])
        logging.info('Connected to email')
        err_message = f"""This is an automatic notification:
Unable to login to {client_data['Client_name']}'s {portal_name} account"""
        logging.info(err_message)
        if client_data['client_type']=="processing":
            if 'Bang' in client_data['Client_name']:
               mail.send_message(subject=f'{portal_name} Login Error!', to=('bpo@bangrealty.com','bpo2@bangrealty.com','loginerror.notify@ecesistech.com','teamsoftware@ecesistech.com','communicationecesis@gmail.com','tvmcommunicationteam@gmail.com','coordinatorecesis@gmail.com','ecesisregnteam@gmail.com','ecesisregn@gmail.com','amar.dev@ecesistech.com','akhil@ecesistech.com','jayakumar@ecesistech.com','sruthi.ss@ecesistech.com','vishnu.m@ecesistech.com'), body=err_message) 
            else:
                #mail.send_message(subject=f'{portal_name} Login Error!', to='exceptionmailsend@gmail.com', body=err_message)
                mail.send_message(subject=f'{portal_name} Login Error!', to=('loginerror.notify@ecesistech.com','teamsoftware@ecesistech.com','communicationecesis@gmail.com','tvmcommunicationteam@gmail.com','coordinatorecesis@gmail.com','ecesisregnteam@gmail.com','ecesisregn@gmail.com','amar.dev@ecesistech.com','akhil@ecesistech.com','jayakumar@ecesistech.com','sruthi.ss@ecesistech.com','vishnu.m@ecesistech.com'), body=err_message)
        else:
            mail.send_message(subject=f'{portal_name} Login Error!', to=email_creds['internal_email_notification'], body=err_message)
        logging.info('Login Error Mail sent')
    except Exception as ex:
        exception_mail_send(portal_name,client_data['Client_name'],ex)
        logging.info(ex)

def inspectionTypeCheck(ordertype, common_db_data)->bool:
    try:
        exterior_inspection_ordertypes=common_db_data['exterior_inspection_ordertypes'].split(',')
        interior_inspection_ordertypes=common_db_data['interior_inspection_ordertypes'].split(',')
        if ((ordertype.lower() in  [x.lower() for x in exterior_inspection_ordertypes]) or (ordertype.lower() in [x.lower() for x in interior_inspection_ordertypes])):
            return True
        return False
    except Exception as ex:
        logging.info(ex)
def zipcode_check(zipcode,ordertype,orderfee,client_data,portal_name):
    common_db_data=cursorexec("order_updation",'SELECT',"""SELECT * FROM `common_data_acceptance` """)
    fee_portal,zipcodedb,typecheck_flag=check_ordertype(ordertype,orderfee,common_db_data,client_data,portal_name)
    zipcodedb={zipcode: True for zipcode in zipcodedb.split(',')}
    inspectionflag = inspectionTypeCheck(ordertype, common_db_data)
    if typecheck_flag:
        if "Bang" in client_data['Client_name'] and inspectionflag == True:
            logging.info('Client is Bang and It is an inspection order')
            if zipcode not in common_db_data['bangnotavailablezip']:                
                reps = velocity_check(zipcode, 15, client_data['Client_name'], portal_name)
                if reps >= 2:
                    return True
                else:
                    return False
            else:
                return False
        else:
            if zipcodedb.get(zipcode,None) is not None :          #Convert to dictionary
                return True 
            else:
                if client_data['Client_name'] in common_db_data['velocityClients']:
                    reps = velocity_check(zipcode,client_data['miles'],client_data['Client_name'],portal_name)
                    if common_db_data['bangnotavailablezip'] is not None:
                    # if client_data['NotavailableZip'] is not None:
                        if zipcode not in common_db_data['bangnotavailablezip']:
                        # if zipcode not in client_data['NotavailableZip']:S
                            if reps >= 2:
                                return True
                            else:
                                return False
                        else:
                            return False
                    else:
                        return False
                else:
                    return False
    else:
        return False
    
def successmessageconditionalyaccept3(client_name, acceptedtime, due_date, providename, orderfee, ordertype, address,order_id,requested_due,msg,requested_fee):
    """This Function returns the order conditionally accepted message template"""
    SUCCESS_MESSAGE = f"""This is an automatic notification that one of your orders was {msg} using our service:

    Client Name: {client_name}
    Accepted Time: {acceptedtime}
    Due Date: {due_date}
    Provider Name: {providename}
    Order Fee: {orderfee}
    Order Type: {ordertype}
    Address: {address}
    OrderID: {order_id}
    Requested Due: {requested_due}
    Requested Fee: {requested_fee}
    """
    return SUCCESS_MESSAGE
