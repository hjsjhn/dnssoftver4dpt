import logging
import docker
import os 

def get_work_dir():
    """Find the path to the project's work directory"""
    return os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]


def get_images(docker_client, work_dir_path):
    """Build DNS software images from Dockerfiles or pull from DockerHub"""

    images = list()

    # Read the list of software
    with open(f"{work_dir}/software/versions_major.txt", "r") as f:
        for software in f:
            # Extract vendor and version information
            vendor, _ , version = software.strip().split("/")
            logging.info("Processing %s-%s", vendor, version)
            # We have Dockerfiles for non-Microsoft software
            if vendor != "microsoft":
                # Store the path to Dockerfile
                path_to_dockerfile = software.strip()
                # Store the image tag
                image_tag = f"{vendor}-{version}"
                # Try to build the image locally
                try:
                    docker_client.images.build(path=f"{work_dir_path}/software/{path_to_dockerfile}", tag=image_tag, rm=True)
                    images.append(f"{image_tag}:latest")
                # If the path to the Dockerfile was not found (the case of some Knot Resolver versions), 
                # we need to pull the official image provided by CZ.NIC 
                except TypeError:
                    if vendor == "knot-resolver":
                        docker_client.images.pull(repository="cznic/knot-resolver", tag=f"v{version}")
                        images.append(f"cznic/knot-resolver:v{version}")
                logging.info("Processed %s-%s", vendor, version)
            else:
                logging.info("Skipping %s-%s", vendor, version)

    return images


def run_containers(images_list, network_custom):
    """Run the containers in our custom network"""

    # Store the container objects
    containers = list()
    for image in images_list:
        logging.info("Starting the %s container", image)
        container_new = client.containers.run(image=image, network = network_custom, detach=True, tty=True)
        containers.append(container_new)

    return containers


def stop_and_remove_containers(containers_list):
    """Stop and remove all our containers running DNS software"""

    # Stop and remove each container one by one
    for container in containers_list:
        logging.info("Stopping the %s container", container.image)
        container.stop()
        logging.info("Removing the %s container", container.image)
        container.remove()


if __name__ == '__main__':

    # Get the working directory
    work_dir = get_work_dir()

    # Configure logging
    logging.basicConfig(filename=f"{work_dir}/logging.log", level=logging.INFO, format='%(asctime)s %(name)s %(processName)s %(threadName)s %(levelname)s:%(message)s')

    # Instantiate the Docker client
    client = docker.from_env()

    # Build Docker images
    images = get_images(docker_client=client, work_dir_path=work_dir)

    # Create a Docker network for this project
    fpdns_network = client.networks.create(name="fpdns")

    # Run containers
    containers = run_containers(images_list=images, network_custom=fpdns_network.name)

    # Stop and remove containers
    stop_and_remove_containers(containers_list=containers)

    # Remove the Docker network
    fpdns_network.remove()
