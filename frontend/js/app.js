/**
 * app.js - Main Application Controller for NovaMart E-Commerce Store
 * Manages State, UI Interactions, Authentication Flows, Activity Logging,
 * and Checkout Security (credentials mandatory only upon ordering).
 */

// Application State
const state = {
    products: [],
    cart: JSON.parse(localStorage.getItem('novamart_cart') || '[]'),
    activeCategory: 'All',
    searchQuery: '',
    sortBy: 'featured',
    detailProduct: null,
    detailQty: 1,
    isBackendLive: false,
    pendingCheckout: false
};

// DOM Selectors
const DOM = {
    // Navbar & Search
    searchInput: document.getElementById('search-input'),
    clearSearchBtn: document.getElementById('clear-search-btn'),
    cartBtn: document.getElementById('cart-btn'),
    cartBadge: document.getElementById('cart-count'),
    historyNavBtn: document.getElementById('history-nav-btn'),

    // Auth & User Menu
    userNavContainer: document.getElementById('user-nav-container'),
    authNavBtn: document.getElementById('auth-nav-btn'),
    userDropdownMenu: document.getElementById('user-dropdown-menu'),
    userDropdownName: document.getElementById('user-dropdown-name'),
    userDropdownEmail: document.getElementById('user-dropdown-email'),
    activityTopBtn: document.getElementById('activity-top-btn'),

    // Catalog Controls
    categoryPills: document.getElementById('category-pills'),
    sortSelect: document.getElementById('sort-select'),
    productGrid: document.getElementById('product-grid'),
    productCount: document.getElementById('product-count'),

    // Cart Drawer
    cartDrawer: document.getElementById('cart-drawer'),
    cartDrawerOverlay: document.getElementById('cart-drawer-overlay'),
    closeCartBtn: document.getElementById('close-cart-btn'),
    cartItemsList: document.getElementById('cart-items-list'),
    cartSubtotal: document.getElementById('cart-subtotal'),
    cartShipping: document.getElementById('cart-shipping'),
    cartTax: document.getElementById('cart-tax'),
    cartTotal: document.getElementById('cart-total'),
    checkoutOpenBtn: document.getElementById('checkout-open-btn'),

    // Product Detail Modal
    detailModal: document.getElementById('detail-modal'),
    detailCloseBtn: document.getElementById('detail-close-btn'),
    detailImg: document.getElementById('detail-img'),
    detailCategory: document.getElementById('detail-category'),
    detailTitle: document.getElementById('detail-title'),
    detailPrice: document.getElementById('detail-price'),
    detailRating: document.getElementById('detail-rating'),
    detailDesc: document.getElementById('detail-desc'),
    detailSpecs: document.getElementById('detail-specs'),
    detailQtyVal: document.getElementById('detail-qty-val'),
    detailQtyMinus: document.getElementById('detail-qty-minus'),
    detailQtyPlus: document.getElementById('detail-qty-plus'),
    detailAddBtn: document.getElementById('detail-add-btn'),

    // Auth Modal
    authModal: document.getElementById('auth-modal'),
    authCloseBtn: document.getElementById('auth-close-btn'),
    authModalTitle: document.getElementById('auth-modal-title'),
    authModalSubtitle: document.getElementById('auth-modal-subtitle'),
    authCheckoutNotice: document.getElementById('auth-checkout-notice'),
    authModalAlert: document.getElementById('auth-modal-alert'),
    tabLoginBtn: document.getElementById('tab-login-btn'),
    tabSignupBtn: document.getElementById('tab-signup-btn'),
    modalLoginForm: document.getElementById('modal-login-form'),
    modalSignupForm: document.getElementById('modal-signup-form'),

    // Activity Modal
    activityModal: document.getElementById('activity-modal'),
    activityCloseBtn: document.getElementById('activity-close-btn'),
    activityFeedList: document.getElementById('activity-feed-list'),
    activityEngineBadge: document.getElementById('activity-engine-badge'),
    activityRefreshBtn: document.getElementById('activity-refresh-btn'),

    // Checkout Modal
    checkoutModal: document.getElementById('checkout-modal'),
    checkoutCloseBtn: document.getElementById('checkout-close-btn'),
    orderForm: document.getElementById('order-form'),
    checkoutSummaryItems: document.getElementById('checkout-summary-items'),
    checkoutTotalAmt: document.getElementById('checkout-total-amt'),
    placeOrderBtn: document.getElementById('place-order-btn'),

    // Confirmation Modal
    confirmModal: document.getElementById('confirm-modal'),
    confirmCloseBtn: document.getElementById('confirm-close-btn'),
    confirmOrderId: document.getElementById('confirm-order-id'),
    confirmDetails: document.getElementById('confirm-details'),
    confirmDoneBtn: document.getElementById('confirm-done-btn'),

    // History Modal
    historyModal: document.getElementById('history-modal'),
    historyCloseBtn: document.getElementById('history-close-btn'),
    historyList: document.getElementById('history-list'),

    // Toast Container
    toastContainer: document.getElementById('toast-container')
};

// ==========================================================================
// Initialization & Backend Check
// ==========================================================================
document.addEventListener('DOMContentLoaded', async () => {
    initEventListeners();
    updateCartBadge();
    updateAuthUI();
    await checkBackendConnection();
    await loadProducts();

    // Log PAGE_VIEW into the SQL database
    window.api.logActivity('PAGE_VIEW', 'Customer opened NovaMart Storefront', {
        userAgent: navigator.userAgent,
        screen: `${window.innerWidth}x${window.innerHeight}`
    });
});

async function checkBackendConnection() {
    try {
        const result = await window.api.checkHealth();
        state.isBackendLive = result.isLive;
        if (DOM.activityEngineBadge && result.engine) {
            DOM.activityEngineBadge.textContent = result.engine.toUpperCase();
        }
    } catch {
        state.isBackendLive = false;
    }
}

// ==========================================================================
// User Authentication & Profile UI
// ==========================================================================
function updateAuthUI() {
    const user = window.api.getCurrentUser();
    const topSignup = document.getElementById('top-signup-link');

    if (user) {
        // User is logged in
        if (topSignup) topSignup.style.display = 'none';

        const initials = user.name
            ? user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
            : 'U';
        const firstName = user.name ? user.name.split(' ')[0] : 'User';

        DOM.authNavBtn.className = 'user-nav-btn logged-in';
        DOM.authNavBtn.innerHTML = `
            <span class="user-avatar-circle">${escapeHtml(initials)}</span>
            <span>Hi, ${escapeHtml(firstName)}</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        `;

        if (DOM.userDropdownName) DOM.userDropdownName.textContent = user.name;
        if (DOM.userDropdownEmail) DOM.userDropdownEmail.textContent = user.email;
    } else {
        // Guest user
        if (topSignup) topSignup.style.display = 'inline';

        DOM.authNavBtn.className = 'user-nav-btn';
        DOM.authNavBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
            </svg>
            <span>Sign In</span>
        `;
        if (DOM.userDropdownMenu) DOM.userDropdownMenu.classList.remove('active');
    }
}

function toggleUserDropdown(e) {
    e.stopPropagation();
    if (!window.api.isAuthenticated()) {
        openAuthModal('login', false);
    } else {
        DOM.userDropdownMenu.classList.toggle('active');
    }
}

function openAuthModal(defaultTab = 'login', isCheckoutTriggered = false) {
    switchAuthTab(defaultTab);
    DOM.authModalAlert.style.display = 'none';

    if (isCheckoutTriggered) {
        state.pendingCheckout = true;
        DOM.authModalTitle.textContent = "Sign In to Checkout";
        DOM.authModalSubtitle.textContent = "Please sign in or create an account with your credentials to complete your purchase.";
        DOM.authCheckoutNotice.style.display = 'flex';
        window.api.logActivity('AUTH_PROMPT_SHOWN', 'Checkout prompt displayed asking for credentials');
    } else {
        state.pendingCheckout = false;
        DOM.authModalTitle.textContent = "Welcome to NovaMart";
        DOM.authModalSubtitle.textContent = "Access your order history and manage your customer profile.";
        DOM.authCheckoutNotice.style.display = 'none';
    }

    DOM.authModal.classList.add('active');
}

function closeAuthModal() {
    DOM.authModal.classList.remove('active');
}

function switchAuthTab(tab) {
    if (tab === 'signup') {
        DOM.tabSignupBtn.classList.add('active');
        DOM.tabLoginBtn.classList.remove('active');
        DOM.modalLoginForm.style.display = 'none';
        DOM.modalSignupForm.style.display = 'block';
    } else {
        DOM.tabLoginBtn.classList.add('active');
        DOM.tabSignupBtn.classList.remove('active');
        DOM.modalLoginForm.style.display = 'block';
        DOM.modalSignupForm.style.display = 'none';
    }
    DOM.authModalAlert.style.display = 'none';
}

function togglePasswordVisibility(fieldId) {
    const input = document.getElementById(fieldId);
    const btn = event.currentTarget;
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = 'Hide';
    } else {
        input.type = 'password';
        btn.textContent = 'Show';
    }
}

function fillModalDemo(email, pass) {
    document.getElementById('modal-login-email').value = email;
    document.getElementById('modal-login-password').value = pass;
}

async function handleModalLogin(e) {
    e.preventDefault();
    DOM.authModalAlert.style.display = 'none';
    const email = document.getElementById('modal-login-email').value.trim();
    const password = document.getElementById('modal-login-password').value;
    const submitBtn = document.getElementById('modal-login-submit');

    submitBtn.disabled = true;
    submitBtn.textContent = 'Verifying Credentials...';

    try {
        const res = await window.api.login({ email, password });
        updateAuthUI();
        closeAuthModal();
        showToast(`Welcome back, ${res.user.name}!`, "success");

        if (state.pendingCheckout) {
            state.pendingCheckout = false;
            openCheckoutModal();
        }
    } catch (err) {
        DOM.authModalAlert.textContent = err.message || 'Invalid credentials';
        DOM.authModalAlert.style.display = 'block';
        DOM.authModalAlert.style.background = '#fef2f2';
        DOM.authModalAlert.style.color = '#b91c1c';
        DOM.authModalAlert.style.border = '1px solid #fecaca';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Sign In & Proceed';
    }
}

async function handleModalSignup(e) {
    e.preventDefault();
    DOM.authModalAlert.style.display = 'none';
    const name = document.getElementById('modal-signup-name').value.trim();
    const email = document.getElementById('modal-signup-email').value.trim();
    const password = document.getElementById('modal-signup-password').value;
    const phone = document.getElementById('modal-signup-phone').value.trim();
    const address = document.getElementById('modal-signup-address').value.trim();
    const submitBtn = document.getElementById('modal-signup-submit');

    if (password.length < 6) {
        DOM.authModalAlert.textContent = 'Password must be at least 6 characters.';
        DOM.authModalAlert.style.display = 'block';
        DOM.authModalAlert.style.background = '#fef2f2';
        DOM.authModalAlert.style.color = '#b91c1c';
        DOM.authModalAlert.style.border = '1px solid #fecaca';
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating Account...';

    try {
        const res = await window.api.signup({ name, email, password, phone, address });
        updateAuthUI();
        closeAuthModal();
        showToast(`Account created! Welcome, ${res.user.name}.`, "success");

        if (state.pendingCheckout) {
            state.pendingCheckout = false;
            openCheckoutModal();
        }
    } catch (err) {
        DOM.authModalAlert.textContent = err.message || 'Failed to create account.';
        DOM.authModalAlert.style.display = 'block';
        DOM.authModalAlert.style.background = '#fef2f2';
        DOM.authModalAlert.style.color = '#b91c1c';
        DOM.authModalAlert.style.border = '1px solid #fecaca';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Account & Proceed';
    }
}

async function handleLogout() {
    DOM.userDropdownMenu.classList.remove('active');
    await window.api.logout();
    updateAuthUI();
    showToast("Signed out successfully", "info");
}

// ==========================================================================
// SQL Activity Log Viewer Modal
// ==========================================================================
async function openActivityModal() {
    DOM.userDropdownMenu.classList.remove('active');
    DOM.activityModal.classList.add('active');
    await loadActivityLogs();
}

function closeActivityModal() {
    DOM.activityModal.classList.remove('active');
}

async function loadActivityLogs() {
    DOM.activityFeedList.innerHTML = `
        <div class="state-container" style="padding:30px 10px;">
            <p>Querying SQL database table <code>activity_logs</code>...</p>
        </div>
    `;

    try {
        const res = await window.api.getActivities(50);
        if (DOM.activityEngineBadge && res.engine) {
            DOM.activityEngineBadge.textContent = res.engine.toUpperCase();
        }

        const activities = res.activities || [];
        if (activities.length === 0) {
            DOM.activityFeedList.innerHTML = `
                <div class="state-container" style="padding:30px 10px;">
                    <h3>No Activities Logged Yet</h3>
                    <p>Start searching products, adding items to cart, or signing up to see live entries.</p>
                </div>
            `;
            return;
        }

        DOM.activityFeedList.innerHTML = activities.map(act => {
            let badgeClass = 'badge-default';
            const action = (act.action || '').toUpperCase();
            if (action.includes('SIGNUP') || action.includes('LOGIN')) badgeClass = 'badge-signup';
            else if (action.includes('ORDER')) badgeClass = 'badge-order';
            else if (action.includes('CART')) badgeClass = 'badge-cart';
            else if (action.includes('SEARCH') || action.includes('VIEW')) badgeClass = 'badge-search';

            const timeStr = act.created_at ? new Date(act.created_at).toLocaleTimeString() : 'Just now';
            const userTag = act.user_email ? `👤 ${escapeHtml(act.user_email)}` : `🌐 Guest (${act.session_id ? act.session_id.substring(0, 10) : 'Anon'})`;

            return `
                <div class="activity-item">
                    <span class="activity-action-badge ${badgeClass}">${escapeHtml(act.action)}</span>
                    <div class="activity-info">
                        <div class="activity-info-header">
                            <span class="activity-desc">${escapeHtml(act.description)}</span>
                            <span class="activity-time">${timeStr}</span>
                        </div>
                        <div class="activity-meta-details">
                            <span>${userTag}</span>
                            ${act.ip_address ? `<span>📍 IP: ${escapeHtml(act.ip_address)}</span>` : ''}
                            ${act.id ? `<span>#ID: ${act.id}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        DOM.activityFeedList.innerHTML = `<div class="state-container"><p>Error retrieving SQL logs: ${err.message}</p></div>`;
    }
}

// ==========================================================================
// Product Fetching & Rendering (Non-Mandatory Auth / Free Browsing)
// ==========================================================================
async function loadProducts() {
    renderLoadingGrid();
    try {
        const result = await window.api.getProducts(state.activeCategory, state.searchQuery);
        state.products = result.data || [];
        applySorting();
        renderProductGrid();
    } catch (err) {
        DOM.productGrid.innerHTML = `
            <div class="state-container">
                <h3>Catalog Temporarily Unavailable</h3>
                <p>We are experiencing a brief maintenance update. Please refresh shortly.</p>
            </div>
        `;
    }
}

function applySorting() {
    if (state.sortBy === 'price-low') {
        state.products.sort((a, b) => a.price - b.price);
    } else if (state.sortBy === 'price-high') {
        state.products.sort((a, b) => b.price - a.price);
    } else if (state.sortBy === 'rating') {
        state.products.sort((a, b) => b.rating - a.rating);
    } else {
        state.products.sort((a, b) => a.id - b.id);
    }
}

function renderLoadingGrid() {
    DOM.productGrid.innerHTML = `
        <div class="state-container">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
                <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
                <path d="M12 2a10 10 0 0 1 10 10"></path>
            </svg>
            <h3>Fetching Catalog...</h3>
            <p>Loading curated tech gear</p>
        </div>
    `;
}

function renderProductGrid() {
    if (DOM.productCount) {
        DOM.productCount.textContent = `${state.products.length} products available`;
    }

    if (state.products.length === 0) {
        DOM.productGrid.innerHTML = `
            <div class="state-container">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <h3>No Products Found</h3>
                <p>We couldn't find any products matching "${escapeHtml(state.searchQuery)}". Try searching for audio, keyboards, or smartwatches.</p>
            </div>
        `;
        return;
    }

    DOM.productGrid.innerHTML = state.products.map(product => `
        <article class="product-card" data-id="${product.id}">
            <div class="card-image-wrap" onclick="openDetailModal(${product.id})">
                <img src="${product.image}" alt="${escapeHtml(product.name)}" loading="lazy">
                <span class="card-category-badge">${escapeHtml(product.category)}</span>
                <span class="card-stock-badge">${product.stock > 0 ? `In Stock (${product.stock})` : 'Sold Out'}</span>
            </div>
            <div class="card-body">
                <div class="card-rating">
                    <span>★ ${product.rating.toFixed(1)}</span>
                    <span class="review-count">(${product.reviews_count || 50} reviews)</span>
                </div>
                <h4 class="card-title" onclick="openDetailModal(${product.id})">${escapeHtml(product.name)}</h4>
                <p class="card-desc">${escapeHtml(product.description)}</p>
                <div class="card-footer">
                    <div class="price-tag">
                        <span class="label">Price</span>
                        <span class="amount">$${product.price.toFixed(2)}</span>
                    </div>
                    <div class="card-actions">
                        <button class="btn-icon" title="Quick View" onclick="openDetailModal(${product.id})">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                        </button>
                        <button class="btn-add-cart" onclick="addToCart(${product.id}, 1)">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="12" y1="5" x2="12" y2="19"></line>
                                <line x1="5" y1="12" x2="19" y2="12"></line>
                            </svg>
                            Add
                        </button>
                    </div>
                </div>
            </div>
        </article>
    `).join('');
}

// ==========================================================================
// Product Detail Modal
// ==========================================================================
async function openDetailModal(productId) {
    try {
        const res = await window.api.getProductById(productId);
        const product = res.data;
        state.detailProduct = product;
        state.detailQty = 1;

        DOM.detailImg.src = product.image;
        DOM.detailImg.alt = product.name;
        DOM.detailCategory.textContent = product.category;
        DOM.detailTitle.textContent = product.name;
        DOM.detailPrice.textContent = `$${product.price.toFixed(2)}`;
        DOM.detailRating.innerHTML = `★ ${product.rating.toFixed(1)} <span class="review-count">(${product.reviews_count || 50} verified buyer reviews)</span>`;
        DOM.detailDesc.textContent = product.description;
        DOM.detailQtyVal.textContent = '1';

        const specs = product.specs || [
            "Official 2-Year Manufacturer Warranty",
            "Express Tracked Courier Shipping (1-3 Days)",
            "30-Day Hassle-Free Returns & Full Refund Guarantee",
            "100% Genuine Certified Hardware"
        ];
        DOM.detailSpecs.innerHTML = specs.map(s => `
            <li>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>${escapeHtml(s)}</span>
            </li>
        `).join('');

        DOM.detailModal.classList.add('active');

        // Log view product detail in SQL DB
        window.api.logActivity('VIEW_PRODUCT_DETAIL', `Inspected product "${product.name}"`, {
            product_id: product.id,
            name: product.name,
            price: product.price
        });
    } catch (err) {
        showToast("Error loading product detail", "error");
    }
}

function closeDetailModal() {
    DOM.detailModal.classList.remove('active');
    state.detailProduct = null;
}

// ==========================================================================
// Shopping Cart Operations (Free to use anonymously)
// ==========================================================================
function addToCart(productId, qtyToAdd = 1) {
    const product = state.products.find(p => p.id === productId) || state.detailProduct;
    if (!product) return;

    const existingIndex = state.cart.findIndex(item => item.id === productId);
    if (existingIndex > -1) {
        state.cart[existingIndex].quantity += qtyToAdd;
    } else {
        state.cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            image: product.image,
            category: product.category,
            quantity: qtyToAdd
        });
    }

    saveCart();
    updateCartBadge();
    animateCartCounter();
    showToast(`Added ${qtyToAdd}x "${product.name}" to cart`, "success");

    // Log ADD_TO_CART into SQL database
    window.api.logActivity('ADD_TO_CART', `Added ${qtyToAdd}x "${product.name}" to cart`, {
        product_id: product.id,
        name: product.name,
        price: product.price,
        quantity: qtyToAdd
    });
}

function updateCartQuantity(productId, delta) {
    const item = state.cart.find(i => i.id === productId);
    if (!item) return;

    item.quantity += delta;
    if (item.quantity <= 0) {
        removeFromCart(productId);
        return;
    }

    saveCart();
    renderCartDrawer();
    updateCartBadge();

    // Log update quantity into SQL database
    window.api.logActivity('UPDATE_CART_QTY', `Updated quantity for "${item.name}" to ${item.quantity}`, {
        product_id: productId,
        new_quantity: item.quantity
    });
}

function removeFromCart(productId) {
    const item = state.cart.find(i => i.id === productId);
    state.cart = state.cart.filter(i => i.id !== productId);
    saveCart();
    renderCartDrawer();
    updateCartBadge();
    if (item) {
        showToast(`Removed "${item.name}" from cart`, "info");
        window.api.logActivity('REMOVE_FROM_CART', `Removed "${item.name}" from cart`, {
            product_id: productId
        });
    }
}

function saveCart() {
    localStorage.setItem('novamart_cart', JSON.stringify(state.cart));
}

function updateCartBadge() {
    const totalCount = state.cart.reduce((sum, item) => sum + item.quantity, 0);
    DOM.cartBadge.textContent = totalCount;
    DOM.cartBadge.style.display = totalCount > 0 ? 'flex' : 'none';
}

function animateCartCounter() {
    DOM.cartBadge.classList.add('bounce');
    setTimeout(() => DOM.cartBadge.classList.remove('bounce'), 250);
}

function getCartCalculations() {
    const subtotal = state.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const shipping = subtotal > 150 || subtotal === 0 ? 0 : 15.00;
    const tax = subtotal * 0.08;
    const total = subtotal + shipping + tax;
    return { subtotal, shipping, tax, total };
}

function openCartDrawer() {
    renderCartDrawer();
    DOM.cartDrawer.classList.add('active');
    DOM.cartDrawerOverlay.classList.add('active');

    window.api.logActivity('OPEN_CART', 'Viewed shopping cart drawer', {
        items_count: state.cart.length
    });
}

function closeCartDrawer() {
    DOM.cartDrawer.classList.remove('active');
    DOM.cartDrawerOverlay.classList.remove('active');
}

function renderCartDrawer() {
    if (state.cart.length === 0) {
        DOM.cartItemsList.innerHTML = `
            <div class="state-container" style="padding: 40px 10px;">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                </svg>
                <h3>Your Cart is Empty</h3>
                <p>Discover our studio headphones, mechanical keyboards, and wearables.</p>
            </div>
        `;
        DOM.checkoutOpenBtn.disabled = true;
    } else {
        DOM.checkoutOpenBtn.disabled = false;
        DOM.cartItemsList.innerHTML = state.cart.map(item => `
            <div class="cart-item">
                <img src="${item.image}" alt="${escapeHtml(item.name)}" class="cart-item-img">
                <div class="cart-item-details">
                    <div class="cart-item-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</div>
                    <div class="cart-item-price">$${item.price.toFixed(2)}</div>
                    <div class="cart-item-controls">
                        <button class="qty-btn" onclick="updateCartQuantity(${item.id}, -1)">-</button>
                        <span class="qty-val">${item.quantity}</span>
                        <button class="qty-btn" onclick="updateCartQuantity(${item.id}, 1)">+</button>
                    </div>
                </div>
                <button class="cart-item-remove" title="Remove Item" onclick="removeFromCart(${item.id})">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        `).join('');
    }

    const { subtotal, shipping, tax, total } = getCartCalculations();
    DOM.cartSubtotal.textContent = `$${subtotal.toFixed(2)}`;
    DOM.cartShipping.textContent = shipping === 0 ? (subtotal > 0 ? 'FREE' : '$0.00') : `$${shipping.toFixed(2)}`;
    DOM.cartTax.textContent = `$${tax.toFixed(2)}`;
    DOM.cartTotal.textContent = `$${total.toFixed(2)}`;
}

// ==========================================================================
// Checkout & Order Placement (MANDATORY CREDENTIALS ONLY HERE)
// ==========================================================================
function openCheckoutModal() {
    if (state.cart.length === 0) {
        showToast("Your cart is empty!", "error");
        return;
    }

    // ENFORCE: Credentials mandatory when ordering!
    if (!window.api.isAuthenticated()) {
        closeCartDrawer();
        openAuthModal('login', true);
        return;
    }

    closeCartDrawer();
    const { subtotal, shipping, tax, total } = getCartCalculations();

    // Pre-fill user profile info
    const user = window.api.getCurrentUser();
    if (user) {
        const nameInput = document.getElementById('input-name');
        const emailInput = document.getElementById('input-email');
        const phoneInput = document.getElementById('input-phone');
        const addressInput = document.getElementById('input-address');
        const cityInput = document.getElementById('input-city');
        const postalInput = document.getElementById('input-postal');

        if (nameInput) nameInput.value = user.name || '';
        if (emailInput) {
            emailInput.value = user.email || '';
            emailInput.readOnly = true;
        }
        if (phoneInput && user.phone) phoneInput.value = user.phone;
        if (addressInput && user.address) addressInput.value = user.address;
        if (cityInput && user.city) cityInput.value = user.city;
        if (postalInput && user.postal) postalInput.value = user.postal;
    }

    DOM.checkoutSummaryItems.innerHTML = state.cart.map(item => `
        <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:0.88rem;">
            <span>${item.quantity}x ${escapeHtml(item.name)}</span>
            <span style="font-weight:700;">$${(item.price * item.quantity).toFixed(2)}</span>
        </div>
    `).join('') + `
        <div style="border-top:1px dashed var(--border-color); padding-top:8px; margin-top:8px; font-size:0.85rem; color:var(--text-secondary);">
            <div style="display:flex; justify-content:space-between;"><span>Subtotal:</span><span>$${subtotal.toFixed(2)}</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Shipping:</span><span>${shipping === 0 ? 'FREE' : '$' + shipping.toFixed(2)}</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Tax (8%):</span><span>$${tax.toFixed(2)}</span></div>
        </div>
    `;

    DOM.checkoutTotalAmt.textContent = `$${total.toFixed(2)}`;
    DOM.checkoutModal.classList.add('active');

    window.api.logActivity('CHECKOUT_INITIATED', 'Customer opened checkout screen', {
        cart_total: total,
        items_count: state.cart.length
    });
}

function closeCheckoutModal() {
    DOM.checkoutModal.classList.remove('active');
}

async function handleOrderSubmit(e) {
    e.preventDefault();

    if (state.cart.length === 0) {
        showToast("Cannot checkout an empty cart.", "error");
        return;
    }

    if (!window.api.isAuthenticated()) {
        closeCheckoutModal();
        openAuthModal('login', true);
        return;
    }

    const formData = new FormData(DOM.orderForm);
    const { subtotal, shipping, tax, total } = getCartCalculations();

    const orderPayload = {
        customer_name: formData.get('name')?.trim(),
        customer_phone: formData.get('phone')?.trim(),
        shipping_address: `${formData.get('address')}, ${formData.get('city')}, ${formData.get('postal')}`,
        payment_method: formData.get('payment_method') || 'Cash on Delivery',
        items: state.cart.map(item => ({
            product_id: item.id,
            name: item.name,
            quantity: item.quantity,
            unit_price: item.price
        })),
        subtotal: parseFloat(subtotal.toFixed(2)),
        shipping_fee: parseFloat(shipping.toFixed(2)),
        tax_amount: parseFloat(tax.toFixed(2)),
        total_amount: parseFloat(total.toFixed(2))
    };

    DOM.placeOrderBtn.disabled = true;
    DOM.placeOrderBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
            <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
            <path d="M12 2a10 10 0 0 1 10 10"></path>
        </svg>
        Securing Order into SQL DB...
    `;

    try {
        const response = await window.api.createOrder(orderPayload);
        const orderData = response.data;

        // Clear cart
        state.cart = [];
        saveCart();
        updateCartBadge();

        // Close checkout and open confirmation
        closeCheckoutModal();
        DOM.orderForm.reset();
        openConfirmationModal(orderData.order_id || 'ORD-SUCCESS', orderPayload);
        showToast("Order saved to SQL database successfully!", "success");
    } catch (err) {
        if (err.auth_required) {
            closeCheckoutModal();
            openAuthModal('login', true);
            showToast("Please sign in with your credentials to complete your order.", "error");
        } else {
            showToast("Failed to place order: " + err.message, "error");
        }
    } finally {
        DOM.placeOrderBtn.disabled = false;
        DOM.placeOrderBtn.innerHTML = `Place Order`;
    }
}

function openConfirmationModal(orderId, orderPayload) {
    DOM.confirmOrderId.textContent = `#${orderId}`;
    DOM.confirmDetails.innerHTML = `
        <p><strong>Customer:</strong> ${escapeHtml(orderPayload.customer_name)}</p>
        <p><strong>Delivery Address:</strong> ${escapeHtml(orderPayload.shipping_address)}</p>
        <p><strong>Payment Method:</strong> ${escapeHtml(orderPayload.payment_method)}</p>
        <p><strong>Total Amount:</strong> $${orderPayload.total_amount.toFixed(2)}</p>
        <p style="margin-top:12px; font-size:0.88rem; color:var(--success); font-weight:600;">
            ✓ Stored in SQL Database &bull; Order Confirmed &bull; Preparing Shipment
        </p>
    `;
    DOM.confirmModal.classList.add('active');
}

function closeConfirmationModal() {
    DOM.confirmModal.classList.remove('active');
}

// ==========================================================================
// Order History Modal
// ==========================================================================
async function openHistoryModal() {
    if (DOM.userDropdownMenu) DOM.userDropdownMenu.classList.remove('active');
    DOM.historyList.innerHTML = `<div class="state-container"><p>Retrieving your order records from SQL database...</p></div>`;
    DOM.historyModal.classList.add('active');

    try {
        const res = await window.api.getOrders();
        const orders = res.data || [];

        if (orders.length === 0) {
            DOM.historyList.innerHTML = `
                <div class="state-container" style="padding:28px 12px;">
                    <h3>No Recent Orders</h3>
                    <p style="margin-bottom:14px;">You haven't placed an order yet, or you are not signed in.</p>
                    <div style="display:flex; justify-content:center; gap:10px;">
                        <a href="orders.html" class="btn-secondary" style="font-size:0.85rem; padding:8px 16px;">Orders Page</a>
                        <a href="login.html?return=orders.html" class="btn-primary" style="font-size:0.85rem; padding:8px 16px;">Sign In</a>
                    </div>
                </div>
            `;
            return;
        }

        DOM.historyList.innerHTML = orders.map(ord => {
            const dateStr = ord.created_at
                ? new Date(ord.created_at.replace(' ', 'T')).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
                : 'Recently Placed';

            const itemsSummary = (ord.items && ord.items.length > 0)
                ? ord.items.map(i => `${i.quantity}x ${escapeHtml(i.product_name)}`).join(', ')
                : 'Verified Purchase Package';

            return `
                <div class="history-card">
                    <div class="history-card-header">
                        <strong>#${escapeHtml(ord.id)}</strong>
                        <span class="order-badge">${escapeHtml(ord.status || 'Confirmed')}</span>
                    </div>
                    <div style="font-size:0.82rem; color:var(--text-muted); margin-bottom:8px;">
                        Date: ${dateStr}
                    </div>
                    <div style="font-size:0.86rem; margin-bottom:6px; color:var(--text-primary);">
                        <strong>Items:</strong> <span style="color:var(--text-secondary);">${itemsSummary}</span>
                    </div>
                    <div style="font-size:0.84rem; margin-bottom:6px;">
                        <strong>Customer:</strong> ${escapeHtml(ord.customer_name || 'Customer')} (${escapeHtml(ord.customer_email || '')})
                    </div>
                    <div style="font-size:0.84rem; margin-bottom:8px;">
                        <strong>Destination:</strong> ${escapeHtml(ord.shipping_address || 'Default Address')}
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-color); padding-top:8px; font-size:0.9rem;">
                        <span>Payment: <strong>${escapeHtml(ord.payment_method || 'COD')}</strong></span>
                        <strong style="color:var(--primary); font-size:1.05rem;">$${parseFloat(ord.total_amount || 0).toFixed(2)}</strong>
                    </div>
                </div>
            `;
        }).join('') + `
            <a href="orders.html" class="btn-primary" style="display:block; text-align:center; padding:10px; margin-top:12px; font-size:0.88rem;">
                Open Full Orders &amp; Shipment Tracking Page &rarr;
            </a>
        `;
    } catch (err) {
        DOM.historyList.innerHTML = `<div class="state-container"><p>Error: ${err.message}</p></div>`;
    }
}

function closeHistoryModal() {
    DOM.historyModal.classList.remove('active');
}

// Export functions to window for inline onclick handlers
window.openHistoryModal = openHistoryModal;
window.closeHistoryModal = closeHistoryModal;
window.openActivityModal = openActivityModal;
window.closeActivityModal = closeActivityModal;
window.handleLogout = handleLogout;

// ==========================================================================
// Toast Notification System
// ==========================================================================
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
        iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    } else if (type === 'error') {
        iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    } else {
        iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `${iconSvg} <span>${escapeHtml(message)}</span>`;
    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}

// Helper: Escape HTML string to avoid XSS vulnerabilities
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ==========================================================================
// Event Listeners Binding
// ==========================================================================
function initEventListeners() {
    // Search input debounced
    let searchDebounce;
    DOM.searchInput.addEventListener('input', (e) => {
        clearTimeout(searchDebounce);
        const val = e.target.value.trim();
        DOM.clearSearchBtn.classList.toggle('visible', val.length > 0);
        searchDebounce = setTimeout(() => {
            state.searchQuery = val;
            loadProducts();
            if (val) {
                window.api.logActivity('SEARCH', `Customer searched for: "${val}"`, { query: val });
            }
        }, 300);
    });

    DOM.clearSearchBtn.addEventListener('click', () => {
        DOM.searchInput.value = '';
        DOM.clearSearchBtn.classList.remove('visible');
        state.searchQuery = '';
        loadProducts();
    });

    // Categories filter
    DOM.categoryPills.addEventListener('click', (e) => {
        const btn = e.target.closest('.category-pill');
        if (!btn) return;
        DOM.categoryPills.querySelectorAll('.category-pill').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.activeCategory = btn.dataset.category;
        loadProducts();

        window.api.logActivity('CATEGORY_FILTER', `Filtered catalog by category: ${state.activeCategory}`, {
            category: state.activeCategory
        });
    });

    // Sorting change
    DOM.sortSelect.addEventListener('change', (e) => {
        state.sortBy = e.target.value;
        applySorting();
        renderProductGrid();

        window.api.logActivity('SORT_CHANGE', `Sorted catalog by: ${state.sortBy}`, {
            sortBy: state.sortBy
        });
    });

    // Auth & Navigation events
    DOM.authNavBtn.addEventListener('click', toggleUserDropdown);
    if (DOM.activityTopBtn) {
        DOM.activityTopBtn.addEventListener('click', openActivityModal);
    }
    if (DOM.activityCloseBtn) DOM.activityCloseBtn.addEventListener('click', closeActivityModal);
    if (DOM.activityRefreshBtn) DOM.activityRefreshBtn.addEventListener('click', loadActivityLogs);
    if (DOM.activityModal) {
        DOM.activityModal.addEventListener('click', (e) => {
            if (e.target === DOM.activityModal) closeActivityModal();
        });
    }

    // Auth modal controls
    DOM.authCloseBtn.addEventListener('click', closeAuthModal);
    DOM.authModal.addEventListener('click', (e) => {
        if (e.target === DOM.authModal) closeAuthModal();
    });
    DOM.modalLoginForm.addEventListener('submit', handleModalLogin);
    DOM.modalSignupForm.addEventListener('submit', handleModalSignup);

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
        if (DOM.userDropdownMenu && !DOM.userNavContainer.contains(e.target)) {
            DOM.userDropdownMenu.classList.remove('active');
        }
    });

    // Cart drawer toggles
    DOM.cartBtn.addEventListener('click', openCartDrawer);
    DOM.closeCartBtn.addEventListener('click', closeCartDrawer);
    DOM.cartDrawerOverlay.addEventListener('click', closeCartDrawer);

    // Detail modal toggles
    DOM.detailCloseBtn.addEventListener('click', closeDetailModal);
    DOM.detailModal.addEventListener('click', (e) => {
        if (e.target === DOM.detailModal) closeDetailModal();
    });

    // Detail quantity adjust
    DOM.detailQtyMinus.addEventListener('click', () => {
        if (state.detailQty > 1) {
            state.detailQty--;
            DOM.detailQtyVal.textContent = state.detailQty;
        }
    });

    DOM.detailQtyPlus.addEventListener('click', () => {
        if (state.detailProduct && state.detailQty < state.detailProduct.stock) {
            state.detailQty++;
            DOM.detailQtyVal.textContent = state.detailQty;
        }
    });

    DOM.detailAddBtn.addEventListener('click', () => {
        if (state.detailProduct) {
            addToCart(state.detailProduct.id, state.detailQty);
            closeDetailModal();
        }
    });

    // Checkout modal toggles
    DOM.checkoutOpenBtn.addEventListener('click', openCheckoutModal);
    DOM.checkoutCloseBtn.addEventListener('click', closeCheckoutModal);
    DOM.checkoutModal.addEventListener('click', (e) => {
        if (e.target === DOM.checkoutModal) closeCheckoutModal();
    });
    DOM.orderForm.addEventListener('submit', handleOrderSubmit);

    // Payment card selection styling
    document.querySelectorAll('.payment-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.payment-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            const radio = card.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
        });
    });

    // Confirmation modal toggles
    DOM.confirmCloseBtn.addEventListener('click', closeConfirmationModal);
    DOM.confirmDoneBtn.addEventListener('click', closeConfirmationModal);

    // History modal toggles
    DOM.historyNavBtn.addEventListener('click', openHistoryModal);
    DOM.historyCloseBtn.addEventListener('click', closeHistoryModal);
    DOM.historyModal.addEventListener('click', (e) => {
        if (e.target === DOM.historyModal) closeHistoryModal();
    });

    // Keyboard ESC key to close any active modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeDetailModal();
            closeCartDrawer();
            closeCheckoutModal();
            closeConfirmationModal();
            closeHistoryModal();
            closeAuthModal();
            closeActivityModal();
            if (DOM.userDropdownMenu) DOM.userDropdownMenu.classList.remove('active');
        }
    });
}
