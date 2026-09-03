const API_BASE="/api/v1";
function getToken(){return localStorage.getItem("access_token")}
function getUser(){const u=localStorage.getItem("user");return u?JSON.parse(u):null}
function setAuth(t,r,u){localStorage.setItem("access_token",t);localStorage.setItem("refresh_token",r);localStorage.setItem("user",JSON.stringify(u))}
function clearAuth(){localStorage.removeItem("access_token");localStorage.removeItem("refresh_token");localStorage.removeItem("user")}
function requireAuth(){if(!getToken()){window.location.href="/login.html";return false}return true}
function redirectIfLoggedIn(){const u=getUser();if(u)window.location.href=u.role==="farmer"?"/farmer/dashboard.html":"/buyer/dashboard.html"}
function logout(){clearAuth();window.location.href="/"}
function toQueryString(params={}){
  const sp=new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if(value === undefined || value === null || value === "") return;
    sp.append(key, String(value));
  });
  return sp.toString();
}

async function apiFetch(path,options={}){
  const token=getToken();
  const headers={"Content-Type":"application/json",...(options.headers||{})};
  if(token)headers["Authorization"]=`Bearer ${token}`;

  const res=await fetch(API_BASE+path,{...options,headers,cache:"no-store"});

  if(res.status===401){
    const rt=localStorage.getItem("refresh_token");
    if(rt){
      try{
        const rr=await fetch(API_BASE+"/auth/refresh",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({refresh_token:rt})});
        if(rr.ok){
          const rd=await rr.json();
          localStorage.setItem("access_token",rd.access_token);
          headers["Authorization"]=`Bearer ${rd.access_token}`;

          const retry=await fetch(API_BASE+path,{...options,headers});
          if(!retry.ok){
            const e=await retry.json().catch(()=>({}));
            throw new Error(e.detail||`Error ${retry.status}`);
          }
          if(retry.status===204)return null;
          return retry.json();
        }else{
          const e=await rr.json().catch(()=>({}));
          throw new Error(e.detail||`Refresh failed (${rr.status})`);
        }
      }catch(e){
        showToast(e.message||"Session expired. Please login again","error");
      }
    }

    clearAuth();
    window.location.href="/login.html";
    return;
  }

  if(!res.ok){
    const err=await res.json().catch(()=>({}));
    throw new Error(err.detail||`Error ${res.status}`)
  }
  if(res.status===204)return null;
  return res.json();
}

const API={
  register:(d)=>apiFetch("/auth/register",{method:"POST",body:JSON.stringify(d)}),
  login:(d)=>apiFetch("/auth/login",{method:"POST",body:JSON.stringify(d)}),
  logout:(d)=>apiFetch("/auth/logout",{method:"POST",body:JSON.stringify(d)}),
  logoutAll:()=>apiFetch("/auth/logout-all",{method:"POST"}),
  refresh:(rt)=>apiFetch("/auth/refresh",{method:"POST",body:JSON.stringify({refresh_token:rt})}),
  me:()=>apiFetch("/auth/me"),
  requestFarmerConversion:(terms_accepted)=>apiFetch("/auth/farmer-conversion/request",{method:"POST",body:JSON.stringify({terms_accepted})}),
  farmerConversionStatus:()=>apiFetch("/auth/farmer-conversion/status"),
  updateMe:(d)=>apiFetch("/auth/me",{method:"PUT",body:JSON.stringify(d)}),
  changePassword:(d)=>apiFetch("/auth/change-password",{method:"POST",body:JSON.stringify(d)}),
  forgotPassword:(phone)=>apiFetch("/auth/forgot-password",{method:"POST",body:JSON.stringify({phone})}),
  resetPassword:(d)=>apiFetch("/auth/reset-password",{method:"POST",body:JSON.stringify(d)}),
  sendVerification:()=>apiFetch("/auth/send-verification",{method:"POST"}),
  verifyPhone:(token)=>apiFetch("/auth/verify-phone",{method:"POST",body:JSON.stringify({verify_token:token})}),
  sessions:()=>apiFetch("/auth/sessions"),
  getUser:(id)=>apiFetch(`/auth/users/${id}`),
  createProduct:(d)=>apiFetch("/products/",{method:"POST",body:JSON.stringify(d)}),
  uploadProductImage: async (file)=>{
    const token=getToken();
    const form=new FormData();
    form.append("file",file);
    const headers={};
    if(token)headers["Authorization"]=`Bearer ${token}`;
    const res=await fetch(API_BASE+"/products/upload-image",{method:"POST",headers,body:form});
    if(!res.ok){const err=await res.json().catch(()=>({}));throw new Error(err.detail||`Error ${res.status}`)}
    return res.json();
  },
  listProducts:(p={})=>apiFetch("/products/?"+toQueryString(p)),
  recommendedProducts:(p={})=>apiFetch("/products/recommended?"+toQueryString(p)),
  getUserProducts:(id)=>apiFetch(`/products/?farmer_id=${id}&limit=100`),
  myProducts:()=>apiFetch("/products/my"),
  getProduct:(id)=>apiFetch(`/products/${id}`),
  updateProduct:(id,d)=>apiFetch(`/products/${id}`,{method:"PUT",body:JSON.stringify(d)}),
  deleteProduct:(id)=>apiFetch(`/products/${id}`,{method:"DELETE"}),
  createDemand:(d)=>apiFetch("/demands/",{method:"POST",body:JSON.stringify(d)}),
  listDemands:(p={})=>apiFetch("/demands/?"+new URLSearchParams(p)),
  myDemands:()=>apiFetch("/demands/my"),
  createOrder:(d)=>apiFetch("/orders/",{method:"POST",body:JSON.stringify(d)}),
  listOrders:()=>apiFetch("/orders/"),
  getOrder:(id)=>apiFetch(`/orders/${id}`),
  updateOrderStatus:(id,status,notes)=>apiFetch(`/orders/${id}/status`,{method:"PATCH",body:JSON.stringify({status,notes})}),
  createPayment:(order_id)=>apiFetch("/payments/create",{method:"POST",body:JSON.stringify({order_id})}),
  verifyPayment:(d)=>apiFetch("/payments/verify",{method:"POST",body:JSON.stringify(d)}),
  releaseEscrow:(order_id)=>apiFetch(`/payments/${order_id}/release-escrow`,{method:"POST"}),
  generateAgreement:(order_id)=>apiFetch(`/agreements/${order_id}/generate`,{method:"POST"}),
  signAgreement:(order_id)=>apiFetch(`/agreements/${order_id}/sign`,{method:"POST"}),
  getMessages:(order_id)=>apiFetch(`/chat/${order_id}/messages`),
  myChatRooms:()=>apiFetch("/chat/rooms/my"),
  matchForDemand:(id)=>apiFetch(`/match/products-for-demand/${id}`),
  matchForProduct:(id)=>apiFetch(`/match/demands-for-product/${id}`),
  createRating:(d)=>apiFetch("/ratings",{method:"POST",body:JSON.stringify(d)}),
  adminStats:()=>apiFetch("/admin/stats"),
  adminKpis:(range="today")=>apiFetch(`/admin/kpis?range=${encodeURIComponent(range)}`),
  adminRevenueSeries:(days=14)=>apiFetch(`/admin/analytics/revenue-series?days=${encodeURIComponent(days)}`),
  adminOrdersSeries:(days=14,status="")=>{
    const p=toQueryString({days,status:status||undefined});
    return apiFetch(`/admin/analytics/orders-series?${p}`);
  },
  adminTopProducts:(limit=10)=>apiFetch(`/admin/analytics/top-products?limit=${encodeURIComponent(limit)}`),
  adminSalesByCategory:(limit=10)=>apiFetch(`/admin/analytics/sales-by-category?limit=${encodeURIComponent(limit)}`),
  adminSalesByPaymentMethod:()=>apiFetch(`/admin/analytics/sales-by-payment-method`),
  adminListOrders:(p={})=>{
    return apiFetch(`/admin/orders?${toQueryString(p)}`);
  },
  // Backward-compat aliases (some pages may reference these)
  adminOrders: (p={})=>API.adminListOrders(p),

  adminListProducts:(p={})=>{
    return apiFetch(`/admin/products?${toQueryString(p)}`);
  },
  adminFarmerConversions:(status="pending")=>apiFetch(`/admin/farmer-conversions?status=${encodeURIComponent(status)}`),
  adminApproveFarmer:(id)=>apiFetch(`/admin/farmer-conversions/approve/${id}`,{method:"POST"}),
  adminApproveAllFarmers:(ids)=>apiFetch("/admin/farmer-conversions/approve-all",{method:"POST",body:JSON.stringify({user_ids:ids})}),
};


function showToast(msg,type="success"){
  let c=document.getElementById("toast-container");
  if(!c){c=document.createElement("div");c.id="toast-container";c.className="toast-container";document.body.appendChild(c)}
  const icons={success:"✅",error:"❌",info:"ℹ️"};
  const t=document.createElement("div");t.className=`toast ${type}`;t.innerHTML=`<span>${icons[type]}</span><span>${msg}</span>`;
  c.appendChild(t);setTimeout(()=>t.remove(),4000);
}

function triggerDashboardRefresh(reason = "status"){
  if (typeof window.refreshDashboardData === "function") {
    window.refreshDashboardData(reason);
    return;
  }
  if (window.location.pathname.includes("/buyer/dashboard.html") || window.location.pathname.includes("/farmer/dashboard.html")) {
    window.location.reload();
  }
}

function startOrderStatusToastWatcher(){
  if(window.__orderStatusToastWatcherStarted) return;
  window.__orderStatusToastWatcherStarted = true;
  const statusText = {
    pending: "Order placed",
    accepted: "Order accepted",
    payment_pending: "Payment pending",
    paid: "Payment confirmed",
    in_transit: "Order dispatched",
    delivered: "Order delivered",
    completed: "Order completed",
    rejected: "Order rejected",
    cancelled: "Order cancelled",
    disputed: "Order disputed"
  };

  const check = async () => {
    try {
      const orders = await API.listOrders();
      const currentUser = getUser() || {};
      const snapshotKey = `agri_order_status_snapshot_${currentUser.id || "guest"}_${currentUser.role || "unknown"}`;
      const productSnapshotKey = `agri_product_stock_snapshot_${currentUser.id || "guest"}_${currentUser.role || "unknown"}`;
      const snapshot = JSON.parse(localStorage.getItem(snapshotKey) || "{}");
      const next = {};
      let changed = false;
      const isFarmer = currentUser.role === "farmer";
      (orders || []).forEach(o => {
        next[o.id] = o.status;
        const prev = snapshot[o.id];
        if (isFarmer && prev === undefined && o.status === "pending") {
          changed = true;
          showToast(`${o.order_number}: New order received`, "info");
        } else if (prev && prev !== o.status) {
          changed = true;
          const label = statusText[o.status] || `Order moved to ${o.status.replace("_", " ")}`;
          showToast(`${o.order_number}: ${label}`, "info");
        }
      });
      localStorage.setItem(snapshotKey, JSON.stringify(next));

      try {
        const products = await API.listProducts({ limit: 200 });
        const productSnapshot = JSON.parse(localStorage.getItem(productSnapshotKey) || "{}");
        const productNext = {};
        (products || []).forEach(p => {
          const qty = Number(p.quantity_kg || 0);
          productNext[p.id] = qty;
          const prevQty = productSnapshot[p.id];
          if (prevQty !== undefined && Number(prevQty) !== qty) {
            changed = true;
            showToast(`${p.name}: stock updated to ${qty}kg`, "info");
          }
        });
        localStorage.setItem(productSnapshotKey, JSON.stringify(productNext));
      } catch (productError) {
        // ignore product snapshot errors
      }

      if (changed) {
        triggerDashboardRefresh("status-change");
      }
    } catch (e) {
      // ignore background polling failures
    }
  };

  check();
  setInterval(check, 8000);
}

function statusBadge(s){return`<span class="status status-${s}">${s.replace("_"," ")}</span>`}
function formatDate(d){if(!d)return"-";return new Date(d).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}
function formatCurrency(n){return"₹"+Number(n).toLocaleString("en-IN",{minimumFractionDigits:2})}

// Convert a product's stored kg quantity into its displayed unit (gram/ton/kg)
function formatQty(p){
  const kg=Number(p?.quantity_kg)||0;
  const unit=(p?.quantity_unit||"kg").toLowerCase();
  if(unit==="gram"||unit==="g"){return trimNum(kg*1000)+" g"}
  if(unit==="ton"||unit==="tonne"||unit==="t"){return trimNum(kg/1000)+" ton"}
  return trimNum(kg)+" kg"
}
function trimNum(n){const r=Math.round(n*100)/100;return (Number.isInteger(r)?r:r.toFixed(2)).toLocaleString("en-IN")}

async function initiatePayment(order_id,onSuccess){
  try{
    const pd=await API.createPayment(order_id);
    if(typeof Razorpay==="undefined" || pd.razorpay_order_id.startsWith("order_demo_")){
      showToast("Demo mode: simulating payment","info");
      await API.verifyPayment({razorpay_order_id:pd.razorpay_order_id,razorpay_payment_id:"demo_pay_"+Date.now(),razorpay_signature:"demo_sig"});
      showToast("Payment successful! 🎉","success");onSuccess&&onSuccess();return;
    }
    new Razorpay({key:pd.key,amount:pd.amount,currency:pd.currency,name:"Agri Marketplace",description:`Order ${pd.order_number}`,order_id:pd.razorpay_order_id,
      handler:async(r)=>{await API.verifyPayment({razorpay_order_id:r.razorpay_order_id,razorpay_payment_id:r.razorpay_payment_id,razorpay_signature:r.razorpay_signature});showToast("Payment verified! Funds in escrow.","success");onSuccess&&onSuccess();},
      theme:{color:"#1a5c2a"}}).open();
  }catch(e){showToast(e.message,"error")}
}

function renderNavbar(){
  const user=getUser();
  const g=document.getElementById("guest-nav");
  const u=document.getElementById("user-nav");
  if(!user){if(g)g.style.display="flex";if(u)u.style.display="none";return}
  if(g)g.style.display="none";
  if(u){u.style.display="flex";const n=document.getElementById("nav-username");const a=document.getElementById("nav-avatar");if(n)n.textContent=user.full_name.split(" ")[0];if(a)a.textContent=user.full_name[0].toUpperCase()}
}
document.addEventListener("DOMContentLoaded",renderNavbar);
