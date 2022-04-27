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
            { item.name }
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
render(() => <Objs />, document.getElementById('objectTable'));

window.s3Proxy.functions.ready(function(){
  window.s3Proxy.functions.getObjects();
});