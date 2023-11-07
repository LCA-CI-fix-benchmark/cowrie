from __future__ import annotations
import json
from configparser import NoOptionError

import oci
import random
import string
import time
import oci
from oci import auth
import datetime

import cowrie.core.output
from cowrie.core.config import CowrieConfig


class Output(cowrie.core.output.Output):
    """
    Oracle Cloud output
    """


    def generate_random_log_id(self):
        random.seed(time.time())
        charset = string.ascii_letters + string.digits
        random_log_id = ''.join(random.choice(charset) for _ in range(32))
        return "cowrielog-" + random_log_id


    def sendLogs(self, logentry):
        log_id = self.generate_random_log_id()
        # Initialize service client with default config file
        current_time = datetime.datetime.utcnow()
        formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")        
        current_time = datetime.datetime.utcnow()
        self.log_ocid = CowrieConfig.get("output_oraclecloud", "log_ocid")

        # Send the request to service, some parameters are not required, see API
        # doc for more info
        put_logs_response = self.loggingingestion_client.put_logs(
            log_id=self.log_ocid,
            put_logs_details=oci.loggingingestion.models.PutLogsDetails(
                specversion="1.0",
                log_entry_batches=[
                    oci.loggingingestion.models.LogEntryBatch(
                        entries=[
                            oci.loggingingestion.models.LogEntry(
                                data=json.dumps(logentry),
                                id=log_id,
                                time=current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))],
                        source="EXAMPLE-source-Value",
                        type="cowrie")]),
            timestamp_opc_agent_processing=current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))

        # Get the data from response
        print(put_logs_response.headers)         

    def start(self):
        """
        Initialize pymisp module and ObjectWrapper (Abstract event and object creation)
        """

        authtype=CowrieConfig.get("output_oraclecloud", "authtype")
     
        if authtype == "instance_principals":
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()

            # In the base case, configuration does not need to be provided as the region and tenancy are obtained from the InstancePrincipalsSecurityTokenSigner
            # identity_client = oci.identity.IdentityClient(config={}, signer=signer)
            self.loggingingestion_client = oci.loggingingestion.LoggingClient(config={}, signer=signer)                     

        if authtype == "user_principals":
            tenancy_ocid=CowrieConfig.get("output_oraclecloud", "tenancy_ocid")
            user_ocid=CowrieConfig.get("output_oraclecloud", "user_ocid")
            region=CowrieConfig.get("output_oraclecloud", "region")
            fingerprint=CowrieConfig.get("output_oraclecloud", "fingerprint")
            priv_key=CowrieConfig.get("output_oraclecloud", "priv_key", raw=True)

            config_with_key_content = {
                "user": user_ocid,
                "key_content": priv_key,
                "fingerprint": fingerprint,
                "tenancy": tenancy_ocid,
                "region": region
            }
            oci.config.validate_config(config_with_key_content)
            self.loggingingestion_client = oci.loggingingestion.LoggingClient(config_with_key_content)


    def stop(self):
        pass

    def write(self, logentry):
        """
        Push to Oracle Cloud put_logs
        """
        # Add the entry to redis
        for i in list(logentry.keys()):
            # Remove twisted 15 legacy keys
            if i.startswith("log_"):
                del logentry[i]
        self.sendLogs(json.dumps(logentry))
