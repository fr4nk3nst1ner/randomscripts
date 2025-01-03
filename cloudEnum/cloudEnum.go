package main

import (
	"bufio"
	//"encoding/csv"
//	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/sts"
	"context"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/lambda"
	"github.com/aws/aws-sdk-go-v2/service/apigateway"
	"github.com/aws/aws-sdk-go-v2/service/apigatewayv2"
	"github.com/aws/aws-sdk-go-v2/service/elasticbeanstalk"
	"github.com/aws/aws-sdk-go-v2/service/cloudfront"
	"encoding/json"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	"github.com/aws/aws-sdk-go-v2/service/ec2/types"
)

const (
	imdsv1URL      = "http://169.254.169.254/latest/meta-data/"
	beanstalkVars  = "http://169.254.169.254/latest/dynamic/instance-identity/document"
	lambdaBaseURL  = "http://localhost:9001/2018-06-01/runtime/invocation/next"
	cloudFrontURL  = "http://169.254.169.254/latest/meta-data/services/domain"
	httpTimeout    = 5 * time.Second
	lambdaTaskRoot = "/var/task"
	lambdaRuntimeDir = "/var/runtime"
	lambdaRuntimeAPI = "AWS_LAMBDA_RUNTIME_API"
)

type Platform int

const (
	IMDSv1 Platform = iota
	Beanstalk
	Lambda
	CloudFront
)

type InstanceIdentity struct {
	Region          string `json:"region"`
	InstanceID      string `json:"instanceId"`
	InstanceType    string `json:"instanceType"`
	AccountID       string `json:"accountId"`
	AvailZone      string `json:"availabilityZone"`
	Architecture    string `json:"architecture"`
	ImageID        string `json:"imageId"`
	PendingTime    string `json:"pendingTime"`
	Version        string `json:"version"`
}

type Options struct {
	Platform     string  // The mode: auth/unauth
	CloudPlatform string // The cloud platform: aws/gcp/azure
	Profile      string
	Action       string
	Unauth       bool
	Auth         struct {
		// AWS options
		AccountsFile     string
		Region          string
		UseOrganization bool
		ResourceType    string  // ami, ebs, ecr

		// GCP options
		ProjectID     string
		GCPResources []string // storage, compute, gke, artifacts

		// Azure options
		SubscriptionID string
		AzureResources []string // storage, compute, acr, aks
	}
	ShowExamples bool // New field for examples flag
}

func printHelp() {
	fmt.Println("Usage: cloudEnum <auth|unauth> [flags]")
	fmt.Println("\nRequired Flags:")
	fmt.Println("  -platform PLATFORM       Cloud platform to use (aws, gcp, azure)")
	fmt.Println("  -action ACTION_NAME      Action to perform")
	fmt.Println("\nPlatform-Specific Required Flags:")
	fmt.Println("  AWS:")
	fmt.Println("    -profile PROFILE       AWS profile (required for unauth mode)")
	fmt.Println("    -accounts-file FILE    File containing AWS account IDs (required for unauth mode)")
	fmt.Println("  GCP:")
	fmt.Println("    -project-id ID         GCP Project ID (required for unauth mode)")
	fmt.Println("  Azure:")
	fmt.Println("    -subscription-id ID    Azure Subscription ID (required for unauth mode)")
	fmt.Println("\nValid Actions by Platform:")
	fmt.Println("  AWS:")
	fmt.Println("    Unauth: ami, ebs, ecr")
	fmt.Println("    Auth:   imdsv1, beanstalk, lambda, cloudfront")
	fmt.Println("  GCP:")
	fmt.Println("    Unauth: storage, compute, gke, artifacts")
	fmt.Println("    Auth:   metadata")
	fmt.Println("  Azure:")
	fmt.Println("    Unauth: acr, aks")
	fmt.Println("    Auth:   imds")
	fmt.Println("\nOptional Flags:")
	fmt.Println("  -region REGION           AWS region (defaults to all regions)")
	fmt.Println("  -use-organization        Use AWS Organizations to discover accounts")
	fmt.Println("  -examples                Show detailed usage examples")
	fmt.Println("\nExample:")
	fmt.Println("  cloudEnum auth -platform aws -action ami -profile myprofile -accounts-file accounts.txt")
	fmt.Println("  cloudEnum unauth -platform aws -action lambda")
	fmt.Println("\nUse -examples flag to see more detailed examples")
}

func printDetailedExamples() {
	fmt.Println("CloudEnum Usage Examples")
	fmt.Println("=======================")
	
	fmt.Println("\nUnauthenticated Mode Examples (API-based enumeration):")
	fmt.Println("------------------------------------------------")
	fmt.Println("AWS:")
	fmt.Println("  AMI enumeration:")
	fmt.Println("    cloudEnum unauth -platform aws -action ami -profile jstinesse -accounts-file accounts.txt")
	fmt.Println("\n  EBS snapshot enumeration:")
	fmt.Println("    cloudEnum unauth -platform aws -action ebs -profile jstinesse -accounts-file accounts.txt")
	fmt.Println("\n  ECR repository enumeration:")
	fmt.Println("    cloudEnum unauth -platform aws -action ecr -profile jstinesse -accounts-file accounts.txt")
	
	fmt.Println("\nGCP:")
	fmt.Println("  Storage bucket enumeration:")
	fmt.Println("    cloudEnum unauth -platform gcp -action storage -project-id primal-prism-193619")
	fmt.Println("\n  Compute instance enumeration:")
	fmt.Println("    cloudEnum unauth -platform gcp -action compute -project-id primal-prism-193619")
	
	fmt.Println("\nAzure:")
	fmt.Println("  Container registry enumeration:")
	fmt.Println("    cloudEnum unauth -platform azure -action acr -subscription-id 606b6e0d-2aa8-4750-a36e-e6b4722119d6")
	fmt.Println("\n  AKS cluster enumeration:")
	fmt.Println("    cloudEnum unauth -platform azure -action aks -subscription-id 606b6e0d-2aa8-4750-a36e-e6b4722119d6")
	
	fmt.Println("\nAuthenticated Mode Examples (Metadata/Runtime service enumeration):")
	fmt.Println("----------------------------------------------------------")
	fmt.Println("AWS:")
	fmt.Println("  IMDSv1 enumeration:")
	fmt.Println("    cloudEnum auth -platform aws -action imdsv1")
	fmt.Println("\n  Lambda runtime enumeration:")
	fmt.Println("    cloudEnum auth -platform aws -action lambda")
	fmt.Println("\n  Beanstalk environment enumeration:")
	fmt.Println("    cloudEnum auth -platform aws -action beanstalk")
	fmt.Println("\n  CloudFront enumeration:")
	fmt.Println("    cloudEnum auth -platform aws -action cloudfront")
	
	fmt.Println("\nGCP:")
	fmt.Println("  Storage service enumeration:")
	fmt.Println("    cloudEnum auth -platform gcp -action storage -project-id primal-prism-193619")
	fmt.Println("\n  Compute service enumeration:")
	fmt.Println("    cloudEnum auth -platform gcp -action compute -project-id primal-prism-193619")
	fmt.Println("\n  GKE cluster enumeration:")
	fmt.Println("    cloudEnum auth -platform gcp -action gke -project-id primal-prism-193619")
	fmt.Println("\n  Artifact registry enumeration:")
	fmt.Println("    cloudEnum auth -platform gcp -action artifacts -project-id primal-prism-193619")
	
	fmt.Println("\nAdditional Options:")
	fmt.Println("------------------")
	fmt.Println("  Specify region (AWS only):")
	fmt.Println("    cloudEnum unauth -platform aws -action ami -profile myprofile -accounts-file accounts.txt -region us-west-2")
	fmt.Println("\n  Use AWS Organizations:")
	fmt.Println("    cloudEnum unauth -platform aws -action ami -profile myprofile -use-organization")
	fmt.Println("\nNote:")
	fmt.Println("  - Unauth mode is for API-based enumeration using credentials")
	fmt.Println("  - Auth mode is for metadata/runtime service enumeration from within cloud resources")
	fmt.Println("  - Use -h or --help for more information about flags and options")
}

func main() {
	var opts Options
	
	// Add examples flag before parsing other arguments
	flag.BoolVar(&opts.ShowExamples, "examples", false, "Show detailed usage examples")
	
	// Parse flags first to check for examples
	flag.Parse()
	
	// If examples flag is set, show examples and exit
	if opts.ShowExamples {
		printDetailedExamples()
		os.Exit(0)
	}

	// Get the mode first (auth/unauth) as it must be the first argument
	if len(os.Args) < 2 {
		printHelp()
		os.Exit(1)
	}

	mode := strings.ToLower(os.Args[1])
	if mode != "auth" && mode != "unauth" {
		fmt.Println("Error: First argument must be either 'auth' or 'unauth'")
		printHelp()
		os.Exit(1)
	}

	// Remove the mode argument before parsing flags
	os.Args = append(os.Args[:1], os.Args[2:]...)

	// Set up command line flags
	flag.StringVar(&opts.Profile, "profile", "", "AWS profile to use")
	flag.StringVar(&opts.Action, "action", "", "Action to perform")
	flag.StringVar(&opts.CloudPlatform, "platform", "", "Cloud platform to use (aws, gcp, azure)")
	
	// AWS auth flags
	flag.StringVar(&opts.Auth.AccountsFile, "accounts-file", "", "Path to file containing AWS account IDs")
	flag.StringVar(&opts.Auth.Region, "region", "", "Specific region to check (default: all regions)")
	flag.BoolVar(&opts.Auth.UseOrganization, "use-organization", false, "Use AWS Organizations to discover accounts")
	
	// GCP auth flags
	flag.StringVar(&opts.Auth.ProjectID, "project-id", "", "GCP Project ID to scan")
	
	// Azure auth flags
	flag.StringVar(&opts.Auth.SubscriptionID, "subscription-id", "", "Azure Subscription ID to scan")
	
	flag.Parse()

	// Validate required flags
	if opts.Action == "" {
		fmt.Println("Error: -action flag is required")
		printHelp()
		os.Exit(1)
	}

	if opts.CloudPlatform == "" {
		fmt.Println("Error: -platform flag is required")
		fmt.Println("Valid platforms: aws, gcp, azure")
		printHelp()
		os.Exit(1)
	}

	opts.Platform = mode
	opts.Unauth = (mode == "unauth")

	// Handle different modes
	if opts.Unauth {
		handleUnauthMode(opts)
	} else {
		handleAuthMode(opts)
	}
}

func isValidPlatform(platform string) bool {
	validPlatforms := map[string]bool{
		"aws":   true,
		"gcp":   true,
		"azure": true,
	}
	return validPlatforms[strings.ToLower(platform)]
}

func handleUnauthMode(opts Options) {
	// First check if the action is valid for the specified platform
	if !isValidUnauthAction(opts.CloudPlatform, opts.Action) {
		fmt.Printf("Error: action '%s' is not valid for platform '%s'\n", opts.Action, opts.CloudPlatform)
		printValidActionsForPlatform(opts.CloudPlatform)
		os.Exit(1)
	}

	switch strings.ToLower(opts.CloudPlatform) {
	case "aws":
		handleAWSUnauth(opts)
	case "gcp":
		handleGCPUnauth(opts)
	case "azure":
		handleAzureUnauth(opts)
	}
}

func handleAWSUnauth(opts Options) {
	switch strings.ToLower(opts.Action) {
	case "ami", "ebs", "ecr":
		if opts.Profile == "" || opts.Auth.AccountsFile == "" {
			fmt.Println("Error: AWS enumeration requires --profile and --accounts-file")
			os.Exit(1)
		}
		enumerateAWSResources(opts)
	case "imdsv1":
		enumerateIMDSv1(opts)
	case "beanstalk":
		enumerateBeanstalkUnauth()
	case "lambda":
		enumerateLambdaUnauth()
	case "cloudfront":
		enumerateCloudFrontUnauth()
	default:
		fmt.Printf("Unknown AWS action: %s\n", opts.Action)
		fmt.Println("Valid AWS unauth actions: ami, ebs, ecr, imdsv1, beanstalk, lambda, cloudfront")
		os.Exit(1)
	}
}

func handleGCPUnauth(opts Options) {
	// Implement GCP unauthenticated enumeration actions
	fmt.Printf("GCP unauthenticated enumeration for action: %s\n", opts.Action)
}

func handleAzureUnauth(opts Options) {
	// Implement Azure unauthenticated enumeration actions
	fmt.Printf("Azure unauthenticated enumeration for action: %s\n", opts.Action)
}

func isValidUnauthAction(platform, action string) bool {
	validActions := map[string]map[string]bool{
		"aws": {
			"ami":        true,
			"ebs":        true,
			"ecr":        true,
			"imdsv1":     true,
			"beanstalk":  true,
			"lambda":     true,
			"cloudfront": true,
		},
		"gcp": {
			"storage":    true,
			"compute":    true,
			"gke":        true,
			"artifacts":  true,
		},
		"azure": {
			"acr":       true,
			"aks":       true,
		},
	}
	
	platformActions, exists := validActions[strings.ToLower(platform)]
	if !exists {
		return false
	}
	return platformActions[strings.ToLower(action)]
}

func printValidActionsForPlatform(platform string) {
	switch strings.ToLower(platform) {
	case "aws":
		fmt.Println("Valid AWS actions: imdsv1, beanstalk, lambda, cloudfront")
	case "gcp":
		fmt.Println("Valid GCP actions: <add valid actions>")
	case "azure":
		fmt.Println("Valid Azure actions: <add valid actions>")
	}
}

func handleAuthMode(opts Options) {
	// Validate platform is specified
	if opts.CloudPlatform == "" {
		fmt.Println("Error: -platform flag is required (aws, gcp, or azure)")
		printHelp()
		os.Exit(1)
	}

	if !isValidPlatform(opts.CloudPlatform) {
		fmt.Printf("Error: invalid platform '%s'\n", opts.CloudPlatform)
		fmt.Println("Valid platforms: aws, gcp, azure")
		printHelp()
		os.Exit(1)
	}

	switch strings.ToLower(opts.CloudPlatform) {
	case "aws":
		switch opts.Action {
		case "imdsv1", "beanstalk", "lambda", "cloudfront":
			enumerateAWSAuth(opts)
		default:
			fmt.Printf("Unknown AWS action: %s\n", opts.Action)
			fmt.Println("Valid AWS auth actions: imdsv1, beanstalk, lambda, cloudfront")
			os.Exit(1)
		}
	case "gcp":
		handleGCPAuth(opts)
	case "azure":
		handleAzureAuth(opts)
	}
}

func handleAWSAuth(opts Options) {
	switch opts.Action {
	case "ami", "ebs", "ecr":
		if opts.Profile == "" || opts.Auth.AccountsFile == "" {
			fmt.Println("Error: AWS enumeration requires --profile and --accounts-file")
			os.Exit(1)
		}
		enumerateAWSResources(opts)
	default:
		fmt.Printf("Unknown AWS action: %s\n", opts.Action)
		fmt.Println("Valid AWS actions: ami, ebs, ecr")
		os.Exit(1)
	}
}

func handleGCPAuth(opts Options) {
	switch opts.Action {
	case "storage", "compute", "gke", "artifacts":
		if opts.Auth.ProjectID == "" {
			fmt.Println("Error: GCP enumeration requires --project-id")
			os.Exit(1)
		}
		enumerateGCPResources(opts)
	default:
		fmt.Printf("Unknown GCP action: %s\n", opts.Action)
		fmt.Println("Valid GCP actions: storage, compute, gke, artifacts")
		os.Exit(1)
	}
}

func handleAzureAuth(opts Options) {
	switch opts.Action {
	case "acr", "aks":
		if opts.Auth.SubscriptionID == "" {
			fmt.Println("Error: Azure enumeration requires --subscription-id")
			os.Exit(1)
		}
		enumerateAzureResources(opts)
	default:
		fmt.Printf("Unknown Azure action: %s\n", opts.Action)
		fmt.Println("Valid Azure actions: acr, aks")
		os.Exit(1)
	}
}

func handleLegacyMode(opts Options) {
	// Original platform-specific enumeration
	switch strings.ToLower(opts.Platform) {
	case "imdsv1":
		enumerateIMDSv1(opts)
	case "beanstalk":
		enumerateBeanstalk(opts)
	case "lambda":
		enumerateLambda(opts)
	case "cloudfront":
		enumerateCloudFront(opts)
	default:
		fmt.Printf("Unknown platform: %s\n", opts.Platform)
		os.Exit(1)
	}
}

func loadAWSConfig(profile string) (aws.Config, error) {
	ctx := context.TODO()
	var cfg aws.Config
	var err error

	if profile == "" {
		cfg, err = config.LoadDefaultConfig(ctx)
	} else {
		cfg, err = config.LoadDefaultConfig(ctx, 
			config.WithSharedConfigProfile(profile),
		)
	}

	if err != nil {
		return cfg, fmt.Errorf("error loading AWS config: %v", err)
	}

	// Verify AWS credentials
	if profile != "" {
		stsClient := sts.NewFromConfig(cfg)
		_, err := stsClient.GetCallerIdentity(ctx, &sts.GetCallerIdentityInput{})
		if err != nil {
			return cfg, fmt.Errorf("error verifying AWS credentials: %v", err)
		}
	}

	return cfg, nil
}

func enumerateIMDSv1(opts Options) {
	cfg, err := loadAWSConfig(opts.Profile)
	if err != nil {
		fmt.Printf("Error loading AWS config: %v\n", err)
		return
	}

	// Get all regions
	regions, err := getAllRegions(cfg)
	if err != nil {
		fmt.Printf("Error getting regions: %v\n", err)
		return
	}

	fmt.Printf("Checking for IMDSv1 enabled instances across %d regions...\n", len(regions))

	for _, region := range regions {
		// Create regional config
		regionalCfg := cfg
		regionalCfg.Region = region
		ec2Client := ec2.NewFromConfig(regionalCfg)

		fmt.Printf("\nRegion: %s\n", region)
		fmt.Println("================")

		// List all instances
		input := &ec2.DescribeInstancesInput{}
		paginator := ec2.NewDescribeInstancesPaginator(ec2Client, input)

		for paginator.HasMorePages() {
			output, err := paginator.NextPage(context.TODO())
			if err != nil {
				fmt.Printf("Error describing instances: %v\n", err)
				continue
			}

			for _, reservation := range output.Reservations {
				for _, instance := range reservation.Instances {
					// Check if IMDSv1 is enabled (HttpTokens is "optional")
					if instance.MetadataOptions != nil && string(instance.MetadataOptions.HttpTokens) == "optional" {
						result := struct {
							InstanceID    string `json:"InstanceID"`
							AllowsIMDSv1  bool   `json:"AllowsIMDSv1"`
						}{
							InstanceID:    *instance.InstanceId,
							AllowsIMDSv1:  true,
						}
						
						// Convert to JSON and print
						jsonOutput, err := json.Marshal(result)
						if err != nil {
							fmt.Printf("Error creating JSON output: %v\n", err)
							continue
						}
						fmt.Println(string(jsonOutput))
					}
				}
			}
		}
	}
}

func enumerateIMDSEndpoint(client *http.Client, url string) {
	resp, err := client.Get(url)
	if err != nil {
		return
	}
	defer resp.Body.Close()

	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		endpoint := scanner.Text()
		if strings.HasSuffix(endpoint, "/") {
			enumerateIMDSEndpoint(client, url+endpoint)
		} else {
			value := getIMDSValue(client, url+endpoint)
			fmt.Printf("%s: %s\n", strings.TrimPrefix(url+endpoint, imdsv1URL), value)
		}
	}
}

func getIMDSValue(client *http.Client, url string) string {
	resp, err := client.Get(url)
	if err != nil {
		return ""
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return ""
	}
	return string(body)
}

func enumerateBeanstalk(opts Options) {
	cfg, err := loadAWSConfig(opts.Profile)
	if err != nil {
		fmt.Printf("Error loading AWS config: %v\n", err)
		return
	}

	// Get all regions
	regions, err := getAllRegions(cfg)
	if err != nil {
		fmt.Printf("Error getting regions: %v\n", err)
		return
	}

	fmt.Printf("Checking Elastic Beanstalk in %d regions...\n", len(regions))

	for _, region := range regions {
		// Create regional config
		regionalCfg := cfg
		regionalCfg.Region = region
		ebClient := elasticbeanstalk.NewFromConfig(regionalCfg)
		
		fmt.Printf("\nRegion: %s\n", region)
		fmt.Println("================")
		
		// Get all applications
		apps, err := ebClient.DescribeApplications(context.TODO(), &elasticbeanstalk.DescribeApplicationsInput{})
		if err != nil {
			fmt.Printf("Error describing applications: %v\n", err)
			continue
		}

		if len(apps.Applications) == 0 {
			fmt.Println("No Elastic Beanstalk applications found")
			continue
		}

		for _, app := range apps.Applications {
			fmt.Printf("\nApplication: %s\n", *app.ApplicationName)
			
			// Get environments for this application
			envs, err := ebClient.DescribeEnvironments(context.TODO(), &elasticbeanstalk.DescribeEnvironmentsInput{
				ApplicationName: app.ApplicationName,
			})
			if err != nil {
				fmt.Printf("Error describing environments: %v\n", err)
				continue
			}

			for _, env := range envs.Environments {
				fmt.Printf("  Environment: %s\n", *env.EnvironmentName)
				fmt.Printf("    - Status: %s\n", string(env.Status))
				fmt.Printf("    - Health: %s\n", string(env.Health))
				if env.CNAME != nil {
					fmt.Printf("    - CNAME: %s\n", *env.CNAME)
				}
				fmt.Printf("    - Platform: %s\n", *env.PlatformArn)
			}
		}
	}
}

func enumerateLambda(opts Options) {
	cfg, err := loadAWSConfig(opts.Profile)
	if err != nil {
		fmt.Printf("Error loading AWS config: %v\n", err)
		return
	}

	// Get all regions
	regions, err := getAllRegions(cfg)
	if err != nil {
		fmt.Printf("Error getting regions: %v\n", err)
		return
	}

	fmt.Printf("Checking Lambda functions in %d regions...\n", len(regions))

	for _, region := range regions {
		// Create regional config and clients
		regionalCfg := cfg
		regionalCfg.Region = region
		lambdaClient := lambda.NewFromConfig(regionalCfg)
		apigatewayClient := apigateway.NewFromConfig(regionalCfg)
		apigatewayv2Client := apigatewayv2.NewFromConfig(regionalCfg)

		fmt.Printf("\nRegion: %s\n", region)
		fmt.Println("================")

		// List all Lambda functions
		paginator := lambda.NewListFunctionsPaginator(lambdaClient, &lambda.ListFunctionsInput{})
		
		for paginator.HasMorePages() {
			output, err := paginator.NextPage(context.TODO())
			if err != nil {
				fmt.Printf("Error listing Lambda functions: %v\n", err)
				continue
			}

			if len(output.Functions) == 0 {
				fmt.Println("No Lambda functions found")
				continue
			}

			for _, function := range output.Functions {
				fmt.Printf("Function: %s\n", *function.FunctionName)

				// Get function's resource policy
				policy, err := lambdaClient.GetPolicy(context.TODO(), &lambda.GetPolicyInput{
					FunctionName: function.FunctionName,
				})
				
				if err == nil {
					fmt.Println("  - Resource Policy:")
					fmt.Printf("    %s\n", *policy.Policy)
				}

				// Get function URL configuration
				urlConfig, err := lambdaClient.GetFunctionUrlConfig(context.TODO(), &lambda.GetFunctionUrlConfigInput{
					FunctionName: function.FunctionName,
				})
				
				if err == nil {
					fmt.Printf("  - Function URL: %s\n", *urlConfig.FunctionUrl)
				}

				// List event source mappings
				mappings, err := lambdaClient.ListEventSourceMappings(context.TODO(), &lambda.ListEventSourceMappingsInput{
					FunctionName: function.FunctionName,
				})
				
				if err == nil {
					fmt.Println("  - Event Source Mappings (Triggers):")
					for _, mapping := range mappings.EventSourceMappings {
						fmt.Printf("    UUID: %s, Source ARN: %s\n", *mapping.UUID, *mapping.EventSourceArn)
					}
				}

				// Check for REST APIs
				apis, err := apigatewayClient.GetRestApis(context.TODO(), &apigateway.GetRestApisInput{})
				if err == nil {
					fmt.Println("  - Associated REST API(s):")
					for _, api := range apis.Items {
						if strings.Contains(*api.Name, *function.FunctionName) {
							stages, err := apigatewayClient.GetStages(context.TODO(), &apigateway.GetStagesInput{
								RestApiId: api.Id,
							})
							if err == nil {
								for _, stage := range stages.Item {
									fmt.Printf("    - Exposed URL: https://%s.execute-api.%s.amazonaws.com/%s\n",
										*api.Id, region, *stage.StageName)
								}
							}
						}
					}
				}

				// Check for HTTP APIs
				httpApis, err := apigatewayv2Client.GetApis(context.TODO(), &apigatewayv2.GetApisInput{})
				if err == nil {
					fmt.Println("  - Associated HTTP API(s):")
					for _, api := range httpApis.Items {
						if strings.Contains(*api.Name, *function.FunctionName) {
							stages, err := apigatewayv2Client.GetStages(context.TODO(), &apigatewayv2.GetStagesInput{
								ApiId: api.ApiId,
							})
							if err == nil {
								for _, stage := range stages.Items {
									fmt.Printf("    - Exposed URL: https://%s.execute-api.%s.amazonaws.com/%s\n",
										*api.ApiId, region, *stage.StageName)
								}
							}
						}
					}
				}

				fmt.Println("-------------------------------------")
			}
		}
	}
}

func enumerateCloudFront(opts Options) {
	cfg, err := loadAWSConfig(opts.Profile)
	if err != nil {
		fmt.Printf("Error loading AWS config: %v\n", err)
		return
	}

	// CloudFront is a global service, use us-east-1
	cfg.Region = "us-east-1"
	
	// Create CloudFront client
	cfClient := cloudfront.NewFromConfig(cfg)

	fmt.Println("Enumerating CloudFront distributions (global service)...")

	// Get list of distributions
	distributions, err := cfClient.ListDistributions(context.TODO(), &cloudfront.ListDistributionsInput{})
	if err != nil {
		fmt.Printf("Error listing CloudFront distributions: %v\n", err)
		return
	}

	if distributions.DistributionList == nil || len(distributions.DistributionList.Items) == 0 {
		fmt.Println("No CloudFront distributions found")
		return
	}

	fmt.Printf("Found %d CloudFront distributions\n", len(distributions.DistributionList.Items))

	// Create slice to store distribution details
	type URLWithPathPattern struct {
		PathPattern string `json:"pathPattern"`
		FullURL     string `json:"fullURL"`
	}

	type DistributionDetails struct {
		DistributionID      string              `json:"distributionId"`
		DomainName         string              `json:"domainName"`
		URLsWithPathPatterns []URLWithPathPattern `json:"urlsWithPathPatterns"`
	}

	var allDistributions []DistributionDetails

	// Iterate through each distribution
	for _, dist := range distributions.DistributionList.Items {
		details := DistributionDetails{
			DistributionID: *dist.Id,
			DomainName:    *dist.DomainName,
		}

		// Get distribution config
		config, err := cfClient.GetDistributionConfig(context.TODO(), &cloudfront.GetDistributionConfigInput{
			Id: dist.Id,
		})
		if err != nil {
			fmt.Printf("Error getting config for distribution %s: %v\n", *dist.Id, err)
			continue
		}

		// Check cache behaviors
		if config.DistributionConfig.CacheBehaviors != nil && len(config.DistributionConfig.CacheBehaviors.Items) > 0 {
			for _, behavior := range config.DistributionConfig.CacheBehaviors.Items {
				// Get origin domain name for the target origin
				var originDomainName string
				for _, origin := range config.DistributionConfig.Origins.Items {
					if *origin.Id == *behavior.TargetOriginId {
						originDomainName = *origin.DomainName
						break
					}
				}

				urlInfo := URLWithPathPattern{
					PathPattern: *behavior.PathPattern,
					FullURL:    originDomainName + *behavior.PathPattern,
				}
				details.URLsWithPathPatterns = append(details.URLsWithPathPatterns, urlInfo)
			}
		}

		allDistributions = append(allDistributions, details)
	}

	// Convert to JSON and print
	output, err := json.MarshalIndent(allDistributions, "", "  ")
	if err != nil {
		fmt.Printf("Error creating JSON output: %v\n", err)
		return
	}

	fmt.Println(string(output))
}

func enumerateBeanstalkUnauth() {
	// Add your unauthenticated Beanstalk enumeration logic here
	fmt.Println("Performing unauthenticated Beanstalk enumeration...")
	// Implementation similar to the original metadata-based approach
}

func enumerateLambdaUnauth() {
	// Add your unauthenticated Lambda enumeration logic here
	fmt.Println("Performing unauthenticated Lambda enumeration...")
	// Implementation similar to the original runtime API-based approach
}

func enumerateCloudFrontUnauth() {
	// Add your unauthenticated CloudFront enumeration logic here
	fmt.Println("Performing unauthenticated CloudFront enumeration...")
	// Implementation similar to the original metadata-based approach
}

func enumerateAWSResources(opts Options) {
	fmt.Printf("Starting AWS resource enumeration for type: %s\n", opts.Auth.ResourceType)
	
	cfg, err := loadAWSConfig(opts.Profile)
	if err != nil {
		fmt.Printf("Error loading AWS config: %v\n", err)
		return
	}

	// Read accounts from file
	accounts, err := readAccountsFile(opts.Auth.AccountsFile)
	if err != nil {
		fmt.Printf("Error reading accounts file: %v\n", err)
		return
	}
	fmt.Printf("Found %d accounts to check\n", len(accounts))

	// Get regions to check
	regions := []string{opts.Auth.Region}
	if opts.Auth.Region == "" {
		regions, err = getAllRegions(cfg)
		if err != nil {
			fmt.Printf("Error getting regions: %v\n", err)
			return
		}
	}
	fmt.Printf("Will check %d regions\n", len(regions))

	// Enumerate resources based on type
	switch opts.Auth.ResourceType {
	case "ami":
		enumerateAMIs(cfg, regions, accounts)
	case "ebs":
		enumerateEBS(cfg, regions, accounts)
	case "ecr":
		enumerateECR(cfg, regions, accounts)
	}
}

func enumerateGCPResources(opts Options) {
	// Implementation for GCP resource enumeration
	fmt.Printf("Enumerating GCP %s resources in project %s...\n", 
		opts.Auth.ResourceType, opts.Auth.ProjectID)
}

func enumerateAzureResources(opts Options) {
	// Implementation for Azure resource enumeration
	fmt.Printf("Enumerating Azure %s resources in subscription %s...\n", 
		opts.Auth.ResourceType, opts.Auth.SubscriptionID)
}

// Helper functions
func readAccountsFile(filepath string) ([]string, error) {
	content, err := os.ReadFile(filepath)
	if err != nil {
		return nil, err
	}
	
	var accounts []string
	for _, line := range strings.Split(string(content), "\n") {
		if account := strings.TrimSpace(line); account != "" {
			accounts = append(accounts, account)
		}
	}
	return accounts, nil
}

func getAllRegions(cfg aws.Config) ([]string, error) {
	// Set initial region to us-east-1 to get list of all regions
	cfg.Region = "us-east-1"
	ec2Client := ec2.NewFromConfig(cfg)
	
	input := &ec2.DescribeRegionsInput{
		AllRegions: aws.Bool(false), // Only enabled regions
	}
	
	result, err := ec2Client.DescribeRegions(context.TODO(), input)
	if err != nil {
		return nil, err
	}

	var regions []string
	for _, region := range result.Regions {
		regions = append(regions, *region.RegionName)
	}
	
	return regions, nil
}

// Resource-specific enumeration functions
func enumerateAMIs(cfg aws.Config, regions, accounts []string) {
	fmt.Println("Enumerating AMIs across regions and accounts...")
	
	for _, region := range regions {
		// Create EC2 client for this region
		regionalCfg := cfg
		regionalCfg.Region = region
		ec2Client := ec2.NewFromConfig(regionalCfg)
		
		fmt.Printf("\nRegion: %s\n", region)
		fmt.Println("================")

		// Check for public AMIs owned by the accounts
		for _, account := range accounts {
			input := &ec2.DescribeImagesInput{
				Owners: []string{account},
				Filters: []types.Filter{
					{
						Name:   aws.String("is-public"),
						Values: []string{"true"},
					},
				},
			}

			result, err := ec2Client.DescribeImages(context.TODO(), input)
			if err != nil {
				fmt.Printf("Error describing images for account %s: %v\n", account, err)
				continue
			}

			if len(result.Images) > 0 {
				fmt.Printf("\nPublic AMIs found for account %s:\n", account)
				for _, image := range result.Images {
					fmt.Printf("  - AMI ID: %s\n", *image.ImageId)
					fmt.Printf("    Name: %s\n", aws.ToString(image.Name))
					fmt.Printf("    Description: %s\n", aws.ToString(image.Description))
					fmt.Printf("    Creation Date: %s\n", aws.ToString(image.CreationDate))
					fmt.Printf("    Public: true\n")
					fmt.Println("    ---")
				}
			}
		}

		// Also check for private AMIs if we have access
		privateInput := &ec2.DescribeImagesInput{
			Owners: accounts,
			Filters: []types.Filter{
				{
					Name:   aws.String("is-public"),
					Values: []string{"false"},
				},
			},
		}

		privateResult, err := ec2Client.DescribeImages(context.TODO(), privateInput)
		if err != nil {
			fmt.Printf("Error describing private images: %v\n", err)
			continue
		}

		if len(privateResult.Images) > 0 {
			fmt.Printf("\nPrivate AMIs found:\n")
			for _, image := range privateResult.Images {
				fmt.Printf("  - AMI ID: %s\n", *image.ImageId)
				fmt.Printf("    Owner: %s\n", *image.OwnerId)
				fmt.Printf("    Name: %s\n", aws.ToString(image.Name))
				fmt.Printf("    Description: %s\n", aws.ToString(image.Description))
				fmt.Printf("    Creation Date: %s\n", aws.ToString(image.CreationDate))
				fmt.Printf("    Public: false\n")
				fmt.Println("    ---")
			}
		}
	}
}

func enumerateEBS(cfg aws.Config, regions, accounts []string) {
	// Implementation for EBS enumeration
}

func enumerateECR(cfg aws.Config, regions, accounts []string) {
	// Implementation for ECR enumeration
}

func enumerateAWSAuth(opts Options) {
	switch opts.Action {
	case "imdsv1":
		enumerateIMDSv1(opts)
	case "beanstalk":
		enumerateBeanstalk(opts)
	case "lambda":
		enumerateLambda(opts)
	case "cloudfront":
		enumerateCloudFront(opts)
	default:
		fmt.Printf("Unknown AWS authenticated action: %s\n", opts.Action)
		fmt.Println("Valid actions: imdsv1, beanstalk, lambda, cloudfront")
		os.Exit(1)
	}
} 