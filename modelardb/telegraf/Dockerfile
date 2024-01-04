FROM golang:1.19

# Set destination for COPY.
WORKDIR /app

# Download Go modules.
COPY Telegraf-Output-Apache-Arrow-Flight/go.mod Telegraf-Output-Apache-Arrow-Flight/go.sum ./
RUN go mod download

# Copy the output plugin source code.
COPY Telegraf-Output-Apache-Arrow-Flight/ ./

RUN CGO_ENABLED=0 GOOS=linux go build -o /binary/flight cmd/main.go
