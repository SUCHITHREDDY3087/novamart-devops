# =============================================================================
# Tier 1: Frontend Nginx Web Server Dockerfile
# Production-ready Alpine Nginx serving static files & reverse-proxying /api
# =============================================================================

FROM nginx:1.27-alpine

# Remove default Nginx website configuration
RUN rm -rf /etc/nginx/conf.d/default.conf

# Copy custom reverse-proxy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static frontend HTML, CSS, and Vanilla JS assets
COPY . /usr/share/nginx/html

# Expose HTTP port 80
EXPOSE 80

# Healthcheck to verify Nginx is actively responding
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
