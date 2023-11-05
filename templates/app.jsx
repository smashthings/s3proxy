import { createSignal } from 'solid-js';
import { render } from 'solid-js/web';

/////////////////////////////////////////////
// Objects
function Objs(){
  const [getObjs, setObjs] = createSignal([{
    "name": "-",
    "last_modified": "-",
    "size": "-",
    "link": "-"
  }]);

  window.s3Proxy.signals.getObjs = getObjs;
  window.s3Proxy.signals.setObjs = setObjs;

  let getObjects = function(){
    let postingDetails = {},
      prefixEle = document.getElementById('searchPrefix'),
      tokenEle = document.getElementById('searchToken'),
      delimiterEle = document.getElementById('searchDelimiter');

    if (prefixEle) {
      postingDetails["prefix"] = prefixEle.value;
    }

    if (tokenEle) {
      postingDetails["token"] = tokenEle.value;
    }

    if (delimiterEle) {
      postingDetails["delimiter"] = delimiterEle.value;
    }

    let successFunc = (resBody)=>{
      let r = JSON.parse(resBody);
      setObjs(r['response']['objs']);
      if (r['response']['token']){
        tokenEle.value = r['response']['token'];
      }
    };
    
    console.log("Fetching objects with settings:");
    console.log(postingDetails);
    window.s3Proxy.functions.postApi("/get-objects", postingDetails, successFunc );
  };

  window.s3Proxy.functions.getObjects = getObjects;
  return (
    <table className="w-full text-sm text-left text-gray-500">
    <thead className="text-xs text-gray-700 uppercase bg-gray-50">
      <tr>
        <th scope="col" className="px-6 py-3">
          Object
        </th>
        <th scope="col" className="px-6 py-3">
          Last Modified
        </th>
        <th scope="col" className="px-6 py-3">
          Size
        </th>
        <th scope="col" className="px-6 py-3">
          <span className="sr-only">Edit</span>
        </th>
      </tr>
    </thead>
    <tbody>

    { getObjs().length > 0 ?
      <For each={getObjs()}>{(item, index) =>
        <tr className="bg-white border-b hover:bg-gray-50">
          <th scope="row" className="px-6 py-4 font-medium text-gray-600 whitespace-nowrap">
            <a href={ item.link } className="font-medium text-blue-600 hover:underline">{ item.name }</a>
          </th>
          <td className="px-6 py-4">
            { item.last_modified }
          </td>
          <td className="px-6 py-4">
            { item.size }
          </td>
          <td className="px-6 py-4 text-right">
            <a href={ item.link } className="font-medium text-blue-600 hover:underline">{ item.link.startsWith("javascript:") ? "List" : "Download"}</a>
          </td>
        </tr>
        }</For>
      : 
      <tr className="bg-white border-b hover:bg-gray-50 text-gray-300/50" style="color: rgba(0, 0, 0, 0.5);">
        <th scope="row" className="px-6 py-4 font-medium text-gray-300/50 text-center whitespace-nowrap" colSpan="4">
          this bucket is empty!
        </th>
      </tr>
      }
    </tbody>
  </table>
  );
}

if (document.getElementById('objectTable')){
  render(() => <Objs />, document.getElementById('objectTable'));
  window.s3Proxy.functions.ready(function(){
    window.s3Proxy.functions.getObjects();
  });
}

/////////////////////////////////////////////
// Notifications
function Notification(props){
  return (
    <div class="pointer-events-auto w-full max-w-sm overflow-hidden hover:overflow-y-auto rounded-lg bg-black text-black shadow-lg ring-black ring-opacity-3 ease-in duration-100 opacity-100 translate-y-0 border-black border-solid border-2 notificationRoot">
      <div class="p-4">
        <div class="flex items-start">
          <div class="flex-shrink-0">
            <svg class={`h-6 w-6 text-${window.s3Proxy.notificationColours[props.msgType]}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d={props.svg} />
            </svg>
          </div>
          <div class="ml-3 w-0 flex-1 pt-0.5">
            <p class="text-sm text-white font-bold">{props.msg}</p>
          </div>
          <div class="ml-4 flex flex-shrink-0">
            <button type="button" class="inline-flex rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2" onclick="this.closest('.notificationRoot').remove();">
              <span class="sr-only">Close</span>
              <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
window.s3Proxy.functions.notification = function(message, msgType){
  let parsedMsgType = ['info', 'warning', 'success', 'error'].includes(msgType) ? msgType : "info",
    notificationsContainer = document.getElementById('notificationsContainer'),
    newEle = Notification({
      msg: message,
      msgType: parsedMsgType,
      svg: window.s3Proxy.svgs[parsedMsgType]
    });
  newEle.classList.add(...window.s3Proxy.notificationStates.entering);
  newEle.classList.add(...window.s3Proxy.notificationStates.enteringBegin);
  notificationsContainer.appendChild(newEle);
  setTimeout(()=>{
    newEle.classList.add(...window.s3Proxy.notificationStates.enteringEnd);
    newEle.classList.remove(...window.s3Proxy.notificationStates.enteringBegin);
  }, 500)
  setTimeout(()=>{
    newEle.classList.add(...window.s3Proxy.notificationStates.leaving);
    newEle.classList.add(...window.s3Proxy.notificationStates.leavingBegin);
    newEle.classList.remove(...window.s3Proxy.notificationStates.entering);
    newEle.classList.remove(...window.s3Proxy.notificationStates.enteringEnd);
  }, 4000 + 500)
  setTimeout(()=>{
    newEle.classList.add(...window.s3Proxy.notificationStates.leavingEnd);
    newEle.classList.remove(...window.s3Proxy.notificationStates.leavingBegin);
  }, 4000 + 2 * 500)
  setTimeout(()=>{
    newEle.remove()
  }, 4000 + 5 * 500)
}

