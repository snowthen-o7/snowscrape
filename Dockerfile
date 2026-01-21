# Dockerfile for SnowScrape JavaScript Renderer
# Based on AWS Lambda Python 3.11 with Playwright and Chromium

FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies for Playwright
RUN yum install -y \
    wget \
    unzip \
    fontconfig \
    freetype \
    libX11 \
    libXcomposite \
    libXdamage \
    libXext \
    libXfixes \
    libXrandr \
    libgbm \
    libxcb \
    libxkbcommon \
    libdrm \
    mesa-libgbm \
    alsa-lib \
    atk \
    cups-libs \
    libXScrnSaver \
    nss \
    nspr \
    pango \
    && yum clean all

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Install Playwright and Chromium
RUN pip install playwright==1.41.0 && \
    playwright install chromium && \
    playwright install-deps chromium

# Copy application code
COPY js_renderer.py ${LAMBDA_TASK_ROOT}/
COPY logger.py ${LAMBDA_TASK_ROOT}/
COPY connection_pool.py ${LAMBDA_TASK_ROOT}/
COPY metrics.py ${LAMBDA_TASK_ROOT}/

# Set environment variables for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/tmp/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Set the CMD to your handler
CMD ["js_renderer.render_handler"]
