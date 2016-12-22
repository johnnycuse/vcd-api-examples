# Extension Example
## Integrating a ticketing system.

For this example, I will be adding in a ticketing system to vCloud Director. This could be an integration into an open source project, existing enterprise tool or even a homegrown system. My goal is to allow my tenants to open up generic tickets at the customer level. In order to add in this functionality I will be utilizing the vCloud Director API extension framework. The code here is described further in a white paper published on the <a href="https://www.vmware.com/content/dam/digitalmarketing/vmware/en/pdf/vcat/vmware-vcloud-api-extension-whitepaper.pdf">VMware VCAT Blog</a>

<b>What is the vCloud Director API extension framework?</b>
<p>The vCloud Director extension framework gives service providers the power to extend the standard API included with vCloud Director. Service providers can register a URL pattern that when called will be routed to custom code to execute via Advanced Message Queuing Protocol (AMQP).  By providing your services as an extension to the vCloud API you provide a single point of integration for your user interface (Custom/3rd Party) as well as your tenant customers. As more customers embrace DevOps it is important to empower them to fully automate against your IaaS platform.</p>

<a href="http://pubs.vmware.com/vcd-80/index.jsp?topic=%2Fcom.vmware.vcloud.api.sp.doc_90%2FGUID-E46CBA12-E81C-4DCB-A68A-1A2B9B0B13CC.html">More Information about the framework can be found here.</a>
