"""Contains all the helper modules which required to run the Valuationconnect acceptance"""
import re
import json
import datetime
import logging
from pytz import timezone
import sender
import requests
import email
import base64
from bs4 import BeautifulSoup
from scrapy.http import HtmlResponse
from stdlib.creds import email_cred
from stdlib.utility import cursorexec,exception_mail_send,client_mail_send,check_ordertype,criteria_with_params,login_into_gmail,write_to_db,successmessageconditionalyaccept

email_creds=email_cred()

class ca:
    def __init__(self,client_data,portal_name):
        self.client_data=client_data
        self.portal_name=portal_name
        self.session = requests.Session()
    def session_check(self):
        try:
            resp=''
            url = "https://vendors.ca-usa.com/Orders/Dashboard"
            if self.client_data['Session_cookie'] != '':
                data = self.client_data['Session_cookie'].split(',')
                cook = 'ASP.NET_SessionId={}; .ASPXAUTH_CLEARVALUE_VENDORPORTAL={};'.format(data[0], data[1])
                # logging.info(cook)
                cookie = {'Cookie': cook}

                resp = self.session.get(url, headers=cookie)
                # logging.info(resp)
                if self.client_data['userid'] in resp.text:
                    logging.info("Session Cookie Active!!! for: {}".format(self.client_data['userid']))
                    self.session.headers.update(cookie)  # session cookie not getting updated after 'get' request
                    return self.session,True
                else:
                    logging.info("Session Cookie Not Active!!!")
                    self.session,login_flag = self.login()
                    return self.session,login_flag
            else:
                self.session,login_flag = self.login()
                return self.session,login_flag
            
        except Exception as ex:
            exception_mail_send(self.portal_name,self.client_data['Client_name'],ex)
            logging.info(ex)

    def extract_mail_content(self,content):
        details = {}
        content= content.get_text()
        details['client_id']=content.split('Vendor ID:')[1].split('Order Number:')[0].strip()
        logging.info("details for: {}".format(details))
        return details

    def checkorder_portal(self):
        try:
            logging.info('Refreshing Portal')
            response = self.session.get("https://vendors.ca-usa.com/Orders/NewOrders?_search=false&nd=1573643709528&rows=-1&page=1&sidx=&sord=asc")
            availbleorders = json.loads(response.content)
            logging.info(availbleorders)
            return self.session,availbleorders
        except Exception as ex:
            exception_mail_send(self.portal_name,self.client_data['Client_name'],ex)
            logging.info(ex)
            
    ####Function for Counter the order-----
    def add_counter_fee(self,count_order):
        try:
            
            logging.info(count_order)
            order_details=count_order['to_accept']
            requested_fee = None
            common_db_data=cursorexec("order_updation",'SELECT',"""SELECT * FROM `common_data_acceptance` """)
            if "Exterior Inspection" in self.client_data['order_quote_ordertypes']  and order_details['VendorProduct'] in common_db_data['exterior_inspection_ordertypes']:requested_fee=self.client_data['order_quote_ext_insp_price']
            if "Exterior" in self.client_data['order_quote_ordertypes']  and order_details['VendorProduct'] in common_db_data['exterior_ordertypes']:requested_fee=self.client_data['order_quote_ext_price']
            if "Interior Inspection" in self.client_data['order_quote_ordertypes'] and order_details['VendorProduct'] in common_db_data['interior_inspection_ordertypes']:requested_fee=self.client_data['order_quote_int_insp_price']
            if "Interior" in self.client_data['order_quote_ordertypes'] and order_details['VendorProduct'] in common_db_data['interior_ordertypes']:requested_fee=self.client_data['order_quote_int_price']
            logging.info('The feerequested is: {}'.format(requested_fee))
            comment = f'I can do this for ${requested_fee}'
            if requested_fee:
                resp = self.session.get("https://vendors.ca-usa.com/Orders/Dashboard")
                soup = BeautifulSoup(resp.content, 'html.parser')
                RequestVerificationToken = soup.find('input', {'name': '__RequestVerificationToken'}).get('value')
                logging.info(RequestVerificationToken)

                data ={
                    '__RequestVerificationToken': RequestVerificationToken,
                    'DeclineOrder.OrderID': order_details['OrderID'],
                    'DeclineOrder.OrderItemID': order_details['OrderItemID'],
                    'DeclineOrder.VendorID': self.client_data['userid'],
                    'DeclineOrder.DeclineReason': 'FEE-NOT-ACCEPTABLE',
                    'DeclineOrder.Comment': comment
                }
                logging.info('The feerequested params is: {}'.format(data))
                
                headers={
                    'authority':'vendors.ca-usa.com',
                    'method':'POST',
                    'path':'/Orders/{}/Items/{}/Decline'.format(order_details['OrderID'],order_details['OrderItemID']),
                    'scheme':'https',
                    'Accept':'application/json, text/javascript, */*; q=0.01',
                    'Accept-Encoding':'gzip, deflate, br, zstd',
                    'Accept-Language':'en-US,en;q=0.9',
                    'Content-Length':'338',
                    'Content-Type':'application/x-www-form-urlencoded',
                    #'Cookie':'__RequestVerificationToken=BCB6vf56rxX0o7vFG_vPdrNORej6wTK0bF_rvBLiZ3oYWcL8Cmfh73NsW24I6gG8qWWJ20BQp9iD8EtARAUlro7XZh01; ASP.NET_SessionId=d3rknuhgjr4cyro1t0jckx5b; .ASPXAUTH_CLEARVALUE_VENDORPORTAL=2_ZMMhfCLfpgEesCqchewFBP7J3D5TU2pfcB1J1Y8l8tZJV6Zzbyubm5KnNQV4YVuKhFyLr6o61ro8T3ozb1ACKyENQcdjPL4VzdQ54fHj3gACEQykalc3tVHuxKiu_1iO95kuMaXsYu_RDkSMhnstDPxJsFOfOcLLrB3afiIV4Acz7J6obsAyvY3kSD3ylTzZ8CR7qfVBpEceV4UH6gqaiveqBK7y4skNWcJogx-ZocShhXWj5Zrz6rlo3m-C7ME2SS029nfc7asOQYrzacK37rQTNY5jD8se7ofbxHMtzlYpb_fx7vC_jMwAj68kLGy3wpd-UcWjI9j_iFFE7zcNBVBIjsqen1MCQsdQVWRj4vlwwRnZykcrtDAVzV6wynNBYorwRO-TfONVEdf7_T6yKz04ccVlwkA1lAkPhIBHHjk5nUKtBGFGtRSu68S5IZ8mHaiI_ljvNdF-oOXggn64rXltZbekXBvaUjm-EwZx-AW4VsUkIJZrpE86ptCZoiLJbENFHmvmH5T9FkI6cAYI183ET3leYxQZgpK-OC_oPx4w4LLD9tOjmFPleKG45Emr9lJk5yJrISG-GsQJNW41kgCd5WABzZ9LiJOcGnhCUfB4Q5qAm6UwbWDOFnywX7LMe1w-yEoArmchgvNK3hB0XtyoNHjE19UYrvrsAnOPlaDt4X3yfpKrfXaEWnKfihBpkU4kPRMADc4J0nOK-C_VqdYYJuvVGcZ0OcxzYbjLWQwd5Gqdvu3CSK8G-ZPqw0VCS5tg',
                    'Origin':'https://vendors.ca-usa.com',
                    'priority': 'u=1, i',
                    'Referer':'https://vendors.ca-usa.com/Orders/Dashboard',
                    'Sec-Ch-Ua':'"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
                    'Sec-Ch-Ua-Mobile':'?0',
                    'Sec-Ch-Ua-Platform':'"Windows"',
                    'Sec-Fetch-Dest':'empty',
                    'Sec-Fetch-Mode':'cors',
                    'Sec-Fetch-Site':'same-origin',
                    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
                    'X-Requested-With':'XMLHttpRequest'
                    }
                
                resp = self.session.post("https://vendors.ca-usa.com/Orders/{}/Items/{}/Decline".format(order_details['OrderID'],order_details['OrderItemID']), data=data, headers=headers)
                logging.info('The feerequested Response is: {} , Address: {}'.format(resp.text,count_order['Address']))
                
                if 'Order %s.%s was successfully declined.'% (order_details['OrderID'], order_details['OrderItemID']) in resp.text:
                    try:
                        subject=f'Fee Change Requested - {self.portal_name}'
                        password ="Ecesis@2024"
                        if self.client_data['from_mail'] == 'bangrealty@bpoacceptor.com':
                            password = 'tvkutrlgskrsijuw'
                            
                        mail = sender.Mail('smtp.gmail.com', self.client_data['from_mail'], password, 465, use_ssl=True,fromaddr=self.client_data['from_mail']) 
                        logging.info('Connected to email For Sending counter offer')
                        msg='Fee Change Requested'
                        mail_message_body = successmessageconditionalyaccept(self.client_data['Client_name'],str(datetime.datetime.now()), count_order['due_date'] ,self.portal_name, count_order['fee_portal'], order_details['VendorProduct'],count_order['Address'],order_details['OrderID'],requested_fee,msg)
                        client_mail_send(mail,self.client_data['to_clientMail'],self.client_data['to_ecesisMail'],subject,mail_message_body)
                        MailStatus='Countered'
                        write_to_db(self.client_data,str(datetime.datetime.now()),order_details['DueDate'],self.portal_name,requested_fee,order_details['VendorProduct'],count_order['Address'],MailStatus,self.portal_name,order_details['OrderID'],subject,count_order['order_received_time'])
                    except Exception as ex:
                        logging.info('Exception Here: {}'.format(ex))
                        MailStatus='Countered'
                        write_to_db(self.client_data,str(datetime.datetime.now()),order_details['DueDate'],self.portal_name,requested_fee,order_details['VendorProduct'],count_order['Address'],MailStatus,self.portal_name,order_details['OrderID'],subject,count_order['order_received_time'])
                    return True
                else:
                    return False
            else:return False
        except Exception as ex:
            logging.info(ex)
            exception_mail_send(self.portal_name,"feerequested-Function",ex) 

    def checkorder_mail(self):
        try:
            conn = login_into_gmail(email_creds['ca_email_address'], email_creds['ca_email_password'])
            conn.select('Inbox')
            retcode, messages = conn.search(None, '(UNSEEN)')
            str_list = list(filter(None, messages[0].decode().split(' ')))
            logging.info('No. of messages for {}: {}'.format(self.portal_name,len(str_list)))
            for message in messages:
                if retcode == 'OK':
                    for num in message.decode().split(' '):
                        if num:
                            logging.info('New order Found!!!')
                            typ, data = conn.fetch(num, '(RFC822)')
                            for response_part in data:
                                if isinstance(response_part, tuple):
                                    msg = email.message_from_bytes(response_part[1])
                                    logging.info(msg['To'])
                                    logging.info(msg['Subject'])

                                    if msg.is_multipart():
                                        mail_body = base64.b64decode(msg.get_payload()[0].get_payload())
                                        soup = BeautifulSoup(mail_body, "lxml")
                                    else:
                                        mail_body = msg.get_payload(decode=True)
                                        soup = BeautifulSoup(mail_body, "lxml")
                                    
                                    order_details=self.extract_mail_content(soup)
                                    return order_details

                        else:
                            return False
        except Exception as ex:
            exception_mail_send(self.portal_name,self.portal_name,ex)
            logging.info(ex)

    def accept_order(self,to_accept,due):
        try: 
            # page = self.session.get('https://vendors.ca-usa.com/Orders/Dashboard')ss
            # soup = BeautifulSoup(page.content, 'html.parser')
            # tokken_new = soup.find('input', {'name': '__RequestVerificationToken'}).get('value')
            accept_url = "https://vendors.ca-usa.com/Orders/{}/Items/{}/Accept" .format(to_accept['OrderID'],to_accept['OrderItemID'])
            response = self.session.post(accept_url)
            response = HtmlResponse(url="my HTML string", body=response.text, encoding='utf-8')
            token_new=response.xpath("//input[contains(@name,'__RequestVerificationToken')]//@value").extract_first()
            data={
                "__RequestVerificationToken": token_new,
                "OrderID": to_accept['OrderID'] ,
                "OrderItemID": to_accept['OrderItemID'],
                "VendorID": self.client_data['userid'],
                "AllowConditionalAcceptance": "false",
                "VendorDueDate": due,
                "VendorAdjustedFee": to_accept['VendorFee'],
                "IsConditionalAcceptance": "false",
                "RequestDate": "",
                "RequestFee": "0.00",
                "Comment":""
                }
            # headers={
            #         'authority':'vendors.ca-usa.com',
            #         'method':'POST',
            #         'path':'/Orders/{}/Items/{}/Accept'.format(to_accept['OrderID'],to_accept['OrderItemID']),
            #         'scheme':'https',
            #         'Accept':'application/json, text/javascript, */*; q=0.01',
            #         'Accept-Encoding':'gzip, deflate, br, zstd',
            #         'Accept-Language':'en-US,en;q=0.9',
            #         'Content-Length':'338',
            #         'Content-Type':'application/x-www-form-urlencoded',
            #         #'Cookie':'__RequestVerificationToken=BCB6vf56rxX0o7vFG_vPdrNORej6wTK0bF_rvBLiZ3oYWcL8Cmfh73NsW24I6gG8qWWJ20BQp9iD8EtARAUlro7XZh01; ASP.NET_SessionId=d3rknuhgjr4cyro1t0jckx5b; .ASPXAUTH_CLEARVALUE_VENDORPORTAL=2_ZMMhfCLfpgEesCqchewFBP7J3D5TU2pfcB1J1Y8l8tZJV6Zzbyubm5KnNQV4YVuKhFyLr6o61ro8T3ozb1ACKyENQcdjPL4VzdQ54fHj3gACEQykalc3tVHuxKiu_1iO95kuMaXsYu_RDkSMhnstDPxJsFOfOcLLrB3afiIV4Acz7J6obsAyvY3kSD3ylTzZ8CR7qfVBpEceV4UH6gqaiveqBK7y4skNWcJogx-ZocShhXWj5Zrz6rlo3m-C7ME2SS029nfc7asOQYrzacK37rQTNY5jD8se7ofbxHMtzlYpb_fx7vC_jMwAj68kLGy3wpd-UcWjI9j_iFFE7zcNBVBIjsqen1MCQsdQVWRj4vlwwRnZykcrtDAVzV6wynNBYorwRO-TfONVEdf7_T6yKz04ccVlwkA1lAkPhIBHHjk5nUKtBGFGtRSu68S5IZ8mHaiI_ljvNdF-oOXggn64rXltZbekXBvaUjm-EwZx-AW4VsUkIJZrpE86ptCZoiLJbENFHmvmH5T9FkI6cAYI183ET3leYxQZgpK-OC_oPx4w4LLD9tOjmFPleKG45Emr9lJk5yJrISG-GsQJNW41kgCd5WABzZ9LiJOcGnhCUfB4Q5qAm6UwbWDOFnywX7LMe1w-yEoArmchgvNK3hB0XtyoNHjE19UYrvrsAnOPlaDt4X3yfpKrfXaEWnKfihBpkU4kPRMADc4J0nOK-C_VqdYYJuvVGcZ0OcxzYbjLWQwd5Gqdvu3CSK8G-ZPqw0VCS5tg',
            #         'Origin':'https://vendors.ca-usa.com',
            #         'priority': 'u=1, i',
            #         'Referer':'https://vendors.ca-usa.com/Orders/Dashboard',
            #         'Sec-Ch-Ua':'"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            #         'Sec-Ch-Ua-Mobile':'?0',
            #         'Sec-Ch-Ua-Platform':'"Windows"',
            #         'Sec-Fetch-Dest':'empty',
            #         'Sec-Fetch-Mode':'cors',
            #         'Sec-Fetch-Site':'same-origin',
            #         'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            #         'X-Requested-With':'XMLHttpRequest'
            #         }
            response = self.session.post(accept_url,data=data)  
            logging.info(response.content.decode())
            if 'Order %s.%s was accepted successfully.' % (to_accept['OrderID'], to_accept['OrderItemID']) in response.content.decode():
                flag_check="accept"
                return flag_check
            else:
                flag_check='Portal Content Changed'
                return flag_check

        except Exception as ex:
            exception_mail_send(self.portal_name,self.client_data['Client_name'],ex)
            logging.info(ex)

    def login(self):
        try:
            logging.info("Logging In for: {}".format(self.client_data['userid']))
            url = "https://vendors.ca-usa.com/Account/Login?ReturnUrl=%2fOrders%2fDashboard"
            response = self.session.post(url)
            soup = HtmlResponse(url="my HTML string", body=response.text, encoding='utf-8')
            token_new=soup.xpath("//input[contains(@name,'__RequestVerificationToken')]//@value").extract_first()

            data = {
                    '__RequestVerificationToken': token_new,
                    'Username': self.client_data['userid'],
                    'Password': self.client_data['password'],
                    'singlebutton:': ''
                }
            resp = self.session.post(url,data=data)

            if f"You are logged in as: {self.client_data['userid']}" in resp.text:
                logging.info('Successfully Logged In for: {}'.format(self.client_data['userid']))
                cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
                logging.info(cookies)
                cursorexec("order_acceptance","UPDATE","""UPDATE ca SET Session_cookie = '{},{}' WHERE userid = '{}'""".format(cookies['ASP.NET_SessionId'], cookies['.ASPXAUTH_CLEARVALUE_VENDORPORTAL'], self.client_data['userid']))
                    
                logging.info("Session Cookie Successfully written to DB for: {}".format(self.client_data['userid']))
                return self.session,True
            else:
                logging.info('Bad Password')
                return self.session,False
        except Exception as ex:
            exception_mail_send(self.portal_name,self.client_data['Client_name'],ex)
            logging.info(ex)


    def criteria_check(self,avail_order):
        try:
            due=str(avail_order['DueDate'])    
            zone = timezone('EST')
            due=due.replace('/Date(','').replace(')/','')
            due=int(due[:-3])
            due = datetime.datetime.fromtimestamp(due, tz=timezone('EST')).strftime("%#m/%#d/%Y") #convert unix time stamp to EST date(without zero padding) 
            today=datetime.datetime.strftime(datetime.datetime.now(zone), '%m/%d/%Y')
            day_1 = datetime.datetime.strptime(today, "%m/%d/%Y")
            day_2 = datetime.datetime.strptime(due, "%m/%d/%Y")

            diff = (day_2 - day_1).days
            logging.info(diff)
            avail_order['VendorProduct']=avail_order['VendorProduct'].strip()
            if (int(avail_order['VendorFee'])>int(avail_order['AdjustedFee'])):
                fee_portal=int(avail_order['VendorFee'])
            else:
                fee_portal=int(avail_order['AdjustedFee'])
            common_db_data=cursorexec("order_updation",'SELECT',"""SELECT * FROM `common_data_acceptance` """)
            address = avail_order['SubjectPropertyAddress1']+' '+avail_order['SubjectPropertyAddress2']+', '+avail_order['SubjectPropertyCity']+', '+avail_order['SubjectPropertyState']+' '+avail_order['SubjectPropertyPostalCode']
            price_in_db,zipcode_in_db,typecheck_flag=check_ordertype(avail_order['VendorProduct'],fee_portal,common_db_data,self.client_data,self.portal_name)
            if typecheck_flag:
                zipcode_in_db={zipcode: True for zipcode in zipcode_in_db.split(',')}
                due,fee_portal,flag=criteria_with_params(price_in_db,zipcode_in_db,fee_portal, diff, avail_order['SubjectPropertyPostalCode'], self.client_data,due,common_db_data,self.portal_name)
                return avail_order,due,self.session,flag,address,fee_portal,diff,due
            else:
                logging.info("Order Type Not Mapped in Database")
                ignored_msg = "Order Type not satisfied"
                return avail_order,ignored_msg,self.session,typecheck_flag,address,fee_portal,diff,due
        except Exception as ex:
            exception_mail_send(self.portal_name,self.client_data['Client_name'],ex)
            logging.info(ex)
