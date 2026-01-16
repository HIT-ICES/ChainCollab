package com.chaincollab.dmn.server;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * DMN Decision Engine Server Main Application
 */
@SpringBootApplication
public class DmnServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(DmnServerApplication.class, args);
        System.out.println("================================================");
        System.out.println("DMN Decision Engine Server 已启动");
        System.out.println("版本: 1.0.0");
        System.out.println("================================================");
        System.out.println("健康检查: GET http://localhost:8080/health");
        System.out.println("执行决策: POST http://localhost:8080/api/dmn/evaluate");
        System.out.println("获取决策信息: POST http://localhost:8080/api/dmn/input-info");
        System.out.println("================================================");
    }
}
