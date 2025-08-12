package org.example.me.asif.astparser;

import java.net.InetAddress;
import py4j.GatewayServer;

public class AstEntryPoint {
    JavaMethodParser3 javaMethodParser = new JavaMethodParser3();
    public AstEntryPoint() {
        // Create a new instance of the AstParser class
//        AstParser astParser = new AstParser();
//        // Start the parser
//        astParser.start();
    }

    public String helloWorld() {
        return "Hello world!";
    }

//    public JavaMethodParser getJavaMethodParser() {
//        return javaMethodParser;
//    }
    public JavaMethodParser3 getJavaMethodParser() {
        return javaMethodParser;
    }

    public FullyQualifiedNameResolver getFullyQualifiedNameResolver() {
        return new FullyQualifiedNameResolver();
    }

    public FullyQualifiedNameResolverMethod getFullyQualifiedNameResolverMethod() {
        return new FullyQualifiedNameResolverMethod();
    }

    public static void main(String[] args) {
        AstEntryPoint astEntryPoint = new AstEntryPoint();
        String host = "0.0.0.0";

        // GatewayServer gatewayServer = new GatewayServer(astEntryPoint, GatewayServer.DEFAULT_PORT, InetAddress.getByName(host));
        // gatewayServer.start();

        GatewayServer server = new GatewayServer(
                astEntryPoint,
                GatewayServer.DEFAULT_PORT,
                0,  // pythonPort (callback), 0 = don’t open one now
                InetAddress.getByName("0.0.0.0"),  // Java listen address
                InetAddress.getByName("0.0.0.0"),  // callback (Python) address if used
                0, 0, null
        );
        server.start();

        System.out.println("Gateway Server Started");
    }
}
