from dotenv import load_dotenv
from github import *
from report import *
from helpers import *
from cache import load_repositories_from_cache, save_repositories_to_cache

load_dotenv()
logger = get_logger()


def read_repo_list(file_path):
    """Read repository names from a file, one per line."""
    repos = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                # Strip whitespace and skip empty lines
                repo_name = line.strip()
                if repo_name:
                    repos.append(repo_name)
        logger.info(f"Loaded {len(repos)} repositories from {file_path}")
        return repos
    except Exception as e:
        logger.error(f"Error reading repo list file: {e}")
        return []


def filter_repositories(repositories, repo_list):
    """Filter repositories to only include those in the provided list."""
    if not repo_list:
        return repositories
    
    filtered_repos = []
    for repo in repositories:
        if repo.name in repo_list:
            filtered_repos.append(repo)
    
    logger.info(f"Filtered from {len(repositories)} to {len(filtered_repos)} repositories")
    return filtered_repos


def main():
    # Parse arguments provided
    args, token = parse_arguments()
    if args.debug:
        logger.setLevel("DEBUG")
        logger.debug("Debug mode activated.")

    # Load repository list if provided
    repo_list = []
    if args.repo_list:
        repo_list = read_repo_list(args.repo_list)

    # Try to load repositories from cache if enabled
    total_repositories = None
    if args.enable_cache:
        logger.info("Cache enabled, checking for cached repositories")
        total_repositories = load_repositories_from_cache()
    
    # If no cache or cache not enabled, fetch repositories from GitHub API
    if total_repositories is None:
        # Gather all data needed for the report - all orgs in the enterprise, repositories in orgs
        orgs_in_ent = get_organizations(args, token)
        logger.info(f"Number of organizations to process: {len(orgs_in_ent)}")
        total_repositories = process_organizations(orgs_in_ent, token)
        
        # Save to cache if enabled
        if args.enable_cache:
            save_repositories_to_cache(total_repositories)

    # Filter repositories if a list was provided
    if repo_list:
        total_repositories = filter_repositories(total_repositories, repo_list)

    logger.info(f"Adding active committers to {len(total_repositories)} repositories")
    add_active_committers(args.ac_report, total_repositories, token)

    # Generate report and print report
    logger.info(f"Generating report...")
    results = generate_max_coverage_report(total_repositories, args.licenses)
    write_report(results, args.output, args.output_format)


if __name__ == "__main__":
    main()
