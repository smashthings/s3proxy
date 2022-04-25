import { createSignal } from 'solid-js';
import { render } from 'solid-js/web';
import "tailwindcss/tailwind.css";

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
    <table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
    <thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
      <tr>
        <th scope="col" class="px-6 py-3">
          Object
        </th>
        <th scope="col" class="px-6 py-3">
          Last Modified
        </th>
        <th scope="col" class="px-6 py-3">
          Size
        </th>
        <th scope="col" class="px-6 py-3">
          <span class="sr-only">Edit</span>
        </th>
      </tr>
    </thead>
    <tbody>

    <For each={getObjs()}>{(item, index) =>
      <tr class="bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600">
        <th scope="row" class="px-6 py-4 font-medium text-gray-900 dark:text-white whitespace-nowrap">
          { item.name }
        </th>
        <td class="px-6 py-4">
          { item.last_modified }
        </td>
        <td class="px-6 py-4">
          { item.size }
        </td>
        <td class="px-6 py-4 text-right">
          <a href={ item.link } class="font-medium text-blue-600 dark:text-blue-500 hover:underline">{ item.link.startsWith("javascript:") ? "List" : "Download"}</a>
        </td>
      </tr>
      }</For>

    </tbody>
  </table>
  );
}
render(() => <Objs />, document.getElementById('objectTable'));

window.s3Proxy.functions.ready(function(){
  window.s3Proxy.functions.getObjects();
});