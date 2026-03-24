module github.com/myorg/service

go 1.22

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/some/package v1.0.0
)

replace github.com/some/package => github.com/myorg/fork main
