import requests
import logging
from scrapy.http import HtmlResponse
from bs4 import BeautifulSoup
import sys
from datetime import datetime
import logging
import time
from random import randint
import json
from pytz import timezone
from stdlib.utility import cursorexec,check_ordertype,criteria_with_params,exception_mail_send

class Amo:
    def __init__(self,client_data) -> None:
        self.client_data=client_data
        
    def get_headers(self,additional_headers):       #Function to fetch the common headers used in the portal
        try:
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform':'"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
                }
            if len(additional_headers)> 0 :
                for a_head in additional_headers: headers[a_head] = additional_headers[a_head]
            return headers
        except Exception as ex:
            logging.info(ex)

    def due_convert_with_diff(self,due,portal_name):        #Function used to convert the due date of an order
        try:
            due=due.replace('/Date(','').replace(')/','')
            due=int(due[:-3])
            duetest=due
            due=datetime.fromtimestamp(due, tz=timezone('EST')).strftime("%#m/%#d/%Y") #convert unix time stamp to EST date(without zero padding)
            zone = timezone('EST')
            today=datetime.strftime(datetime.now(zone), '%m/%d/%Y')
            d1 = datetime.strptime(today, "%m/%d/%Y")
            d2 = datetime.strptime(due, "%m/%d/%Y")
            diff=((d2 - d1).days)
            return due,diff,duetest
        except Exception as ex:
            logging.info("Exception Occured{}{} ".format(ex,self.client_data['Client_name']))          
            logging.info("ERROR ON LINE {},{},{}".format(sys.exc_info()[-1].tb_lineno,type(ex).__name__,ex,self.client_data['Client_name']))     
            exception_mail_send(portal_name,self.client_data['Client_name'],ex)

    def login(self, isLoggedIn, userid, client_name,portal_name):       #Function used t login into the portal
        try:      
            logging.info(" Trying to Log In...")
            session = requests.Session()
            response = session.get("https://valvp.amoservices.com/Account/Login?ReturnUrl=%2F")
            # logging.info(f"Login token response: {response.text}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            token = soup.find(
                'input', {'name': '__RequestVerificationToken'}).get('value')        
            headers=self.get_headers({})
            data = {'__RequestVerificationToken': token,
                    'ReCAPTCHAModel.V2Response': '',
                    'ReCAPTCHAModel.V3Response': '',
                    'Username': userid,
                    'Password': self.client_data['password']}        
            response = session.post('https://valvp.amoservices.com/Account/Login?ReturnUrl=%2F', data=data, headers= headers)
            # logging.info(f"Login data: {data}")
            # logging.info(f"Login headers: {headers}")
            # logging.info(f"Login succ resp: {response.content.decode()}")
            if "You are logged in as" in (response.content.decode()):
                isLoggedIn = True
            else:
                isLoggedIn = False
            return isLoggedIn,session
        except Exception as ex:
            logging.info("Exception Occured{} {}".format(ex,client_name) )             
            logging.info("ERROR ON LINE {},{},{}".format(sys.exc_info()[-1].tb_lineno,type(ex).__name__,ex,self.client_data['Client_name']))     
            exception_mail_send(portal_name,self.client_data['Client_name'],ex)

    def check_orders(self,session,portal_name):     #Function to fetch the orders from the portal
        try:
            response = session.get('https://valvp.amoservices.com/Orders/Dashboard')
            # logging.info(f" Accept token resp: {response.text}")
            response = HtmlResponse(url="my HTML string", body=response.text, encoding='utf-8')
            accept_token=response.xpath("//input[contains(@name,'__RequestVerificationToken')]//@value").extract_first()
            response = session.get('https://valvp.amoservices.com/Orders/NewOrders?_search=false&nd=1714576408409&rows=-1&page=1&sidx=&sord=asc')
            cookies = requests.utils.dict_from_cookiejar(session.cookies)
            resp_json = json.loads(response.content)

            orders = resp_json['rows']
            
            if resp_json['records'] == 10:
                logging.info("No New Orders Available in portal {}, Order: {}".format(self.client_data['Client_name'],resp_json))    
                logging.info(" {}{} ".format(orders, self.client_data['Client_name']))
                return False,orders,session,accept_token
            else:
            
                logging.info("Orders Are Available -{} {} ".format(len(orders),self.client_data['Client_name']))
                logging.info(" {}{} ".format(orders, self.client_data['Client_name']))
                # orders=[{'OrderID': 1720974, 'OrderItemID': 1, 'ProductID': 1162, 'Product': 'iPCR Ext', 'ClientID': 58452, 'Client': 'VELOCITY COMMUNITY FCU', 'Recipient': 'VELOCITY COMMUNITY FCU', 'RecipientAddress1': '2801 PGA BLVD', 'RecipientAddress2': 'Suite 120', 'RecipientCity': 'Palm Beach Gardens', 'RecipientState': 'FL', 'RecipientPostalCode': '33410', 'SubjectPropertyAddress1': '3330 Morning Dove Dr', 'SubjectPropertyAddress2': '', 'SubjectPropertyCity': 'Deland', 'SubjectPropertyState': 'FL', 'SubjectPropertyPostalCode': '32720', 'UnhandledComment': False, 'LockboxCode': '', 'LoanPurposeID': 'REFINANCE', 'LoanPurposeDescription': 'Refinance', 'LoanTypeID': 'OTHER', 'LoanTypeDescription': 'Other', 'FHACaseNumber': '', 'LoanNumber': '5353680', 'OnHold': False, 'HideClientDetails': False, 'Overdue': False, 'DueDate': '/Date(1705957487200)/', 'InspectedDate': None, 'Borrower': 'JAMES WATKINS', 'ServiceRepName': '', 'AppointmentRequired': True, 'Latitude': 29.087844848632812, 'Longitude': -81.33154296875, 'RushOrder': False, 'AnalyticsProviderID': '', 'ConfirmAppointment': False, 'VendorProduct': 'iPCR Ext', 'AssignedDate': '/Date(1705611915457)/', 'AllowsConditionals': False, 'TimeSensitiveTaskType': 'TentativeAssignment', 'VendorFee': 30.0, 'AdjustedFee': 30.0, 'VendorTechnologyFee': 0, 'Reviewer': '', 'EngagementDocumentID': None, 'SuppliedApptTime1': None, 'SuppliedApptTime2': None, 'SuppliedApptEndTime1': None, 'SuppliedApptEndTime2': None, 'PreventVendorAccess': False, 'IsMapAvailable': True, 'OrderKey': '1720974.1', 'IsBusy': False, 'IsSelfBusy': False}]
                return True,orders,session,accept_token            
        except Exception as ex:
            logging.info("Exception Occured{} {}".format(ex,self.client_data['Client_name']))             
            logging.info("ERROR ON LINE {},{},{}".format(sys.exc_info()[-1].tb_lineno,type(ex).__name__,ex,self.client_data['Client_name']))     
            exception_mail_send(portal_name,self.client_data['Client_name'],ex)

    def criteria_check(self,avail_order,session,portal_name):       #Function  to check the criteria of an order
        try:
            
            fee_portal=avail_order['VendorFee']
            if (int(avail_order['VendorFee'])>int(avail_order['AdjustedFee'])):
                fee_portal=int(avail_order['VendorFee'])
            else:
                fee_portal=int(avail_order['AdjustedFee'])
            due=avail_order['DueDate']
            due,diff,duetest=self.due_convert_with_diff(due,portal_name)       #check due date difference 
            zipcode = avail_order['SubjectPropertyPostalCode']     
            common_db_data=cursorexec("order_updation",'SELECT',f"""SELECT * FROM `common_data_acceptance` """)                
            price_in_db,zipcode_in_db,typecheck_flag=check_ordertype(avail_order['VendorProduct'],avail_order['VendorFee'],common_db_data,self.client_data,portal_name)  #check order type  is satisfied or not       
            if typecheck_flag:
                zipcode_in_db={zipcode: True for zipcode in zipcode_in_db.split(',')}
                due,fee_portal,flag=criteria_with_params(price_in_db,zipcode_in_db, fee_portal, diff, zipcode, self.client_data,due,common_db_data,portal_name) # check zipcode, fee and due date satisfied or not.
                return avail_order,due,fee_portal,session,flag
            else:             
                ignored_msg = "Order Type not satisfied"
                return avail_order,ignored_msg,fee_portal,session,typecheck_flag           
        except Exception as ex:
            logging.info(ex)
            exception_mail_send(portal_name,self.client_data['Client_name'],ex)

    def accept_orders(self,to_accept,session,accept_token,portal_name):        #Fucntion to accept and order
            try:
                orderid= to_accept['OrderID']
                orderitemid=to_accept['OrderItemID']
                due=to_accept['DueDate']
                due,diff,duetest=self.due_convert_with_diff(due,portal_name)
                logging.info("DUE DATE---{}{}".format(due,self.client_data['Client_name']))
                cookies = requests.utils.dict_from_cookiejar(session.cookies)            
                headers=[]
                headers.append(self.get_headers({'X-Requested-With': 'XMLHttpRequest'}) )   
                dueformat=datetime.fromtimestamp(duetest,tz=timezone('Asia/Kolkata')).isoformat()
                data={
                        "__RequestVerificationToken": accept_token,
                        "OrderID": orderid ,
                        "OrderItemID": orderitemid,
                        "VendorID": self.client_data['userid'],
                        "AllowConditionalAcceptance": "true",
                        "VendorDueDate": dueformat,
                        "VendorAdjustedFee": to_accept['AdjustedFee'],
                        "IsConditionalAcceptance": "false",
                        "RequestDate": "",
                        "RequestFee": "0.00",
                        "Comment":"",
                        'checkAcceptOrderTnC': 'checkAcceptOrderTnC'
                        }
                response = session.post("https://valvp.amoservices.com/Orders/{}/Items/{}/Accept".format(orderid,orderitemid),data=data,headers=headers[0])
                # logging.info(response.text)
                # logging.info(f"Accept order data: {data}")
                # logging.info(f"Accept order headers: {headers}")
                if 'Order %s.%s was accepted successfully.'% (orderid,orderitemid) in response.text:
                        due_date = due
                        order_fee = to_accept['AdjustedFee']
                        address = to_accept['SubjectPropertyAddress1']+' '+to_accept['SubjectPropertyAddress2']+', '+to_accept['SubjectPropertyCity']+', '+to_accept['SubjectPropertyState']+' '+to_accept['SubjectPropertyPostalCode']
                        prod_type = to_accept['VendorProduct']                
                        logging.info("Order Accepted {}  Due Date-{}  Order Type - {}  {}".format(address,due_date,prod_type,self.client_data['Client_name']))
                        return True,due_date,address                   
                else:   
                        return  False,due_date,address            
            except Exception as ex:
                logging.info("Exception Occured{} {}".format(ex,self.client_data['Client_name']))             
                logging.info("ERROR ON LINE {},{},{}".format(sys.exc_info()[-1].tb_lineno,type(ex).__name__,ex,self.client_data['Client_name']))     
                exception_mail_send(portal_name,self.client_data['Client_name'],ex)
                time.sleep(randint(60,90))

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
                # params.update({
                #     "accept_order|%s" % order_details['order_id'] : orderid,
                #     "requested_fee|%s" % order_details['order_id'] : requested_fee,
                #     "comments|%s" % order_details['order_id'] : "FEE-NOT-ACCEPTABLE"
                # })  
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
                # logging.info(response.text)
                # logging.info(f"Counter order data: {data}")
                # logging.info(f"Counter order headers: {headers}")
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
