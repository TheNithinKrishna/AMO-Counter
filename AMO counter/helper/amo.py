"""Contains all the helper modules which required to run the Valuationconnect acceptance"""
import re
import requests
from scrapy.http import HtmlResponse
from bs4 import BeautifulSoup
import sys
import datetime
import logging
from pytz import timezone
import requests
import email
import json
from stdlib.creds import email_cred
from stdlib.utility import cursorexec,exception_mail_send,check_ordertype,criteria_with_params,login_into_gmail

email_creds=email_cred()

class amo:
    def __init__(self,client_data,portal_name):
        self.client_data=client_data
        self.portal_name=portal_name
        self.session = requests.Session()
        
    def session_check(self):
        try:
            resp=''
            session = requests.Session()
            url = "https://valvp.amoservices.com/Orders/Dashboard"
            if self.client_data['Session_cookie'] != '':
                data = self.client_data['Session_cookie'].split(',')
                cook = 'ASP.NET_SessionId={}; .ASPXAUTH_CLEARVALUE_VENDORPORTAL={};'.format(data[0], data[1])
                # logging.info(cook)
                cookie = {'Cookie': cook}

                resp = self.session.get(url, headers=cookie)
                # logging.info(resp.text)
                if str(self.client_data['userid']) in resp.text:
                    logging.info("Session Cookie Active!!! for: {}".format(self.client_data['userid']))
                    self.session.headers.update(cookie)  # session cookie not getting updated after 'get' request
                    return session,True
                else:
                    logging.info("Session Cookie Not Active!!!")
                    session,resp,login_flag = self.login()
                    return session,login_flag
            else:
                session,resp,login_flag = self.login()
                return session,login_flag
        except Exception as ex:
            exception_mail_send(self.portal_name,self.client_data['Client_name'],ex)
            logging.info(ex)

    def get_headers(self,additonal_headers):  #Function to fetch the default headers used in acceptance
        try:
            headers={
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Connection': 'keep-alive',
                    'Host': 'valvp.amoservices.com',
                    'Referer': 'https://valvp.amoservices.com/Account/Login',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
                    }
            
            if len(additonal_headers)> 0 :
                for a_head in additonal_headers: headers[a_head] = additonal_headers[a_head]
            return headers
        except Exception as ex:
            logging.info(ex)

    def checkorder_portal(self):    #Fetch orders from portal
        try:
            logging.info('Refreshing Portal')
            headers=self.get_headers({'Sec-Fetch-Dest': 'empty','Sec-Fetch-Mode': 'cors','Sec-Fetch-Site': 'same-origin','X-Requested-With': 'XMLHttpRequest','Referer': 'https://valvp.amoservices.com/Orders/Dashboard'})
            response = self.session.get("https://valvp.amoservices.com/Orders/NewOrders?_search=false&nd=1597838044743&rows=-1&page=1&sidx=&sord=asc",headers=headers)
            availbleorders = json.loads(response.content)
            logging.info(availbleorders)
            return self.session,availbleorders
        except Exception as ex:
            exception_mail_send(self.portal_name,self.client_data['Client_name'],ex)
            logging.info(ex)    

    def checkorder_mail(self):          #Check whether order mails came and fetch the email address 
        try:
            conn = login_into_gmail(email_creds['amo_email_address'], email_creds['amo_email_password'])
            conn.select('inbox')
            retcode, data = conn.search(None, '(SUBJECT "New Assignment Notice" UNSEEN)')
            str_list = list(filter(None, data[0].decode().split(' ')))
            logging.info('No: of unread messages AMO: {}'.format(len(str_list)))
            
            if retcode == 'OK':
                for num in data[0].decode().split(' '):
                    if num:
                        type, data = conn.fetch(num, '(RFC822)' )
                        for response_part in data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_string(response_part[1].decode('utf-8'))
                                to_address = msg['To']
                                if '<' in to_address:
                                    to_address=to_address.split('<')[1]
                                if '>' in to_address:
                                    to_address=to_address.split('>')[0]
                                if ',' in to_address:
                                    to_address=to_address.split(',')[0]
                                
                                return to_address
                    else:
                        return False
        except Exception as ex:
            exception_mail_send(self.portal_name,self.portal_name,ex)
            logging.info(ex)

    def accept_order(self,to_accept,due):       #Function used for accepting an order
        try: 
            accept_url = "https://valvp.amoservices.com/Orders/{}/Items/{}/Accept" .format(to_accept['OrderID'],to_accept['OrderItemID'])
            response = self.session.get("https://valvp.amoservices.com/Orders/Dashboard")
            #logging.info(f"Token fetching response: {response.text}")
            response = HtmlResponse(url="my HTML string", body=response.text, encoding='utf-8')
            token_new=response.xpath("//input[contains(@name,'__RequestVerificationToken')]//@value").extract_first()
            # logging.info(token_new)
            due=to_accept['DueDate']
            import datetime
            s_time = re.sub("\D", '', to_accept['DueDate'])
            due = datetime.datetime.fromtimestamp(float(s_time) / 1000).strftime('%m/%d/%Y')
            logging.info(due)
            dd=datetime.datetime.fromtimestamp(float(s_time) / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")
            acceptdue = dd.replace('Z','+05:30')

            data={
                '__RequestVerificationToken': token_new,
                'OrderID': to_accept['OrderID'],
                'OrderItemID': to_accept['OrderItemID'],
                'VendorID': self.client_data['userid'],
                'AllowConditionalAcceptance': 'false',
                'VendorDueDate': acceptdue,
                'VendorAdjustedFee': to_accept['AdjustedFee'],
                'IsConditionalAcceptance': 'false',
                'RequestDate': '',
                'RequestFee': '0.00',
                'Comment': '',
                'checkAcceptOrderTnC': 'checkAcceptOrderTnC'
                }
            
            headers=self.get_headers({'Origin': 'https://valvp.amoservices.com','Sec-Fetch-Dest': 'empty','Sec-Fetch-Mode': 'cors','Sec-Fetch-Site': 'same-origin','X-Requested-With': 'XMLHttpRequest','Referer': 'https://valvp.amoservices.com/Orders/Dashboard'})
            response = self.session.post(accept_url,data=data,headers=headers)
            if 'Order %s.%s was accepted successfully.' % (to_accept['OrderID'], to_accept['OrderItemID']) in response.text:
                flag_check='accept'
                return flag_check
            else:
                flag_check='Portal Content Changed'
                return flag_check

        except Exception as ex:
            exception_mail_send(self.portal_name,self.client_data['Client_name'],ex)
            logging.info(ex)

    def login(self):        #Function used to login into the portal
        try:
            logging.info("Logging In for: {}".format(self.client_data['userid']))
            response = self.session.post("https://valvp.amoservices.com/Account/Login?object=form-horizontal%20well")
            # logging.info(f"Login token resp: {response.text}")
            soup = HtmlResponse(url="my HTML string", body=response.text, encoding='utf-8')
            token_new=soup.xpath("//input[contains(@name,'__RequestVerificationToken')]//@value").extract_first()
            
            data = {
                '__RequestVerificationToken': token_new,
                'Username': self.client_data['userid'],
                'Password': self.client_data['password'],
                'singlebutton': ''
                }
            headers=self.get_headers({'Cache-Control': 'max-age=0','Origin': 'https://valvp.amoservices.com','Upgrade-Insecure-Requests': '1'})
            resp = self.session.post("https://valvp.amoservices.com/Account/Login?object=form-horizontal%20well",headers=headers,data=data)
            if f"You are logged in as: {self.client_data['userid']}" in resp.text:
                logging.info('Successfully Logged In for: {}'.format(self.client_data['userid']))
                cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
                # logging.info(cookies)
                cursorexec("order_acceptance","UPDATE","""UPDATE AMO SET Session_cookie = '{},{}' WHERE userid = '{}'""".format(cookies['ASP.NET_SessionId'], cookies['.ASPXAUTH_CLEARVALUE_VENDORPORTAL'], self.client_data['userid']))
                
                logging.info("Session Cookie Successfully written to DB for: {}".format(self.client_data['userid']))
                return self.session,resp,True
            else:
                logging.info('Bad Password')
                return self.session,resp,False
        except Exception as ex:
            exception_mail_send(self.portal_name,self.client_data['Client_name'],ex)
            logging.info(ex)

    def criteria_check(self,avail_order):       #Function used to check the criteria of the order
        try:
            due=str(avail_order['DueDate'])
            zone = timezone('EST')
            due=due.replace('/Date(','').replace(')/','')
            due=int(due[:-3])
            due = datetime.datetime.fromtimestamp(due).strftime("%m/%d/%Y")    
            today=datetime.datetime.strftime(datetime.datetime.now(zone), '%m/%d/%Y')
            day_1 = datetime.datetime.strptime(today, "%m/%d/%Y")
            day_2 = datetime.datetime.strptime(due, "%m/%d/%Y")
            
            diff = (day_2 - day_1).days
            logging.info(diff)
            if (int(avail_order['VendorFee'])>int(avail_order['AdjustedFee'])):
                fee_portal=int(avail_order['VendorFee'])
            else:
                fee_portal=int(avail_order['AdjustedFee'])
            address = avail_order['SubjectPropertyAddress1']+' '+avail_order['SubjectPropertyAddress2']+', '+avail_order['SubjectPropertyCity']+', '+avail_order['SubjectPropertyState']+' '+avail_order['SubjectPropertyPostalCode']
            common_db_data=cursorexec("order_updation",'SELECT',"""SELECT * FROM `common_data_acceptance` """)
            price_in_db,zipcode_in_db,typecheck_flag=check_ordertype(avail_order['VendorProduct'],fee_portal,common_db_data,self.client_data,self.portal_name)
            if typecheck_flag:
                zipcode_in_db={zipcode: True for zipcode in zipcode_in_db.split(',')}
                due,fee_portal,flag=criteria_with_params(price_in_db,zipcode_in_db,fee_portal, diff, avail_order['SubjectPropertyPostalCode'], self.client_data,due,common_db_data,self.portal_name)
                return avail_order,due,self.session,flag,address,fee_portal
            else:
                logging.info("Order Type Not Mapped in Database")
                ignored_msg = "Order Type not satisfied"
                return avail_order,ignored_msg,self.session,typecheck_flag,address,fee_portal
        except Exception as ex:
            exception_mail_send(self.portal_name,self.client_data['Client_name'],ex)
            logging.info(ex)
            
    def add_counter_fee(self,to_counter,session,common_db_data):
        try:
            requested_fee=None
            if "Exterior Inspection" in self.client_data['order_quote_ordertypes']  and to_counter['Product'] in common_db_data['exterior_inspection_ordertypes']:
                    requested_fee=self.client_data['order_quote_ext_insp_price']
            elif "Exterior" in self.client_data['order_quote_ordertypes']  and to_counter['Product'] in common_db_data['exterior_ordertypes']:
                    requested_fee=self.client_data['order_quote_ext_price']
            elif "Interior" in self.client_data['order_quote_ordertypes'] and to_counter['Product'] in common_db_data['interior_ordertypes']:
                if "Interior Inspection" in self.client_data['order_quote_ordertypes'] and to_counter['Product'] in common_db_data['interior_inspection_ordertypes']:
                    requested_fee=self.client_data['order_quote_int_insp_price']
                else:
                    requested_fee=self.client_data['order_quote_int_price']
            if requested_fee:
                logging.info('The feerequested is: {}'.format(requested_fee))
                orderid =to_counter['OrderID']   
                print("OrderID",orderid)
                orderitemid=to_counter['OrderItemID']
                print(orderitemid)  
                Decline_url = "https://valvp.amoservices.com/Orders/{}/Items/{}/Decline".format(orderid,orderitemid)
                due=to_counter['DueDate']
                try:
                    due=due.replace('/Date(','').replace(')/','')
                    print(due)
                    due=int(due[:-3])
                    due=datetime.fromtimestamp(due, tz=timezone('EST')).strftime("%#m/%#d/%Y")
                    print(due)
                    print('Duedate:',due)
                except Exception as ex:                                     
                    # print('Due date',ex,due)
                    logging.info(due)
                response = session.get("https://valvp.amoservices.com/Account/Login?ReturnUrl=%2F")
                # logging.info(f"Counter token resp: {response.text}")
                soup = BeautifulSoup(response.content, 'html.parser')
                token = soup.find(
                    'input', {'name': '__RequestVerificationToken'}).get('value')    
                headers = self.get_headers({
                                'authority': 'valvp.amoservices.com',
                                'method': 'POST',
                                'path': '/Orders/{}/Items/{}/Decline'.format(orderid,orderitemid),
                                'scheme': 'https',
                                'Accept': 'application/json, text/javascript, */*; q=0.01',
                                'accept-encoding': 'gzip, deflate, br',
                                'accept-language': 'en-US,en;q=0.9',
                                'origin': 'https://valvp.amoservices.com',
                                'referer': 'https://valvp.amoservices.com/Orders/Dashboard',
                                'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not=A?Brand";v="24"',
                                'sec-ch-ua-mobile': '?0',
                                'sec-ch-ua-platform': '"Windows"',
                                'sec-fetch-dest': 'empty',
                                'sec-fetch-mode': 'cors',
                                'sec-fetch-site': 'same-origin',
                                'x-requested-with': 'XMLHttpRequest'
                                })
                data = {
                        '__RequestVerificationToken':token,
                        'DeclineOrder.OrderID':orderid, 
                        'DeclineOrder.OrderItemID': orderitemid,
                        'DeclineOrder.VendorID': self.client_data['userid'],
                        'DeclineOrder.DeclineReason':'FEE-NOT-ACCEPTABLE',
                        'DeclineOrder.Comment': requested_fee
                    }
                response = session.post(Decline_url,data=data,headers=headers)
                print(response.text)
                if 'Order %s.%s was successfully declined.'% (to_counter['OrderID'],to_counter['OrderItemID']) in response.text:
                    # print('order declined')
                    logging.info('order declined')
                    return True,requested_fee,due
                else:
                    return False,requested_fee,due
            else:
                return False,requested_fee,due
        except Exception as ex:
                        # print('Exception in counter function',ex)
                        logging.info('Exception here....')
                        exception_mail_send("amo",self.client_data['client_name'],ex)        
