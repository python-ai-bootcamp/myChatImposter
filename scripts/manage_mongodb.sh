#!/bin/bash
# manage_mongodb.sh

set -e

BACKUP_DIR="./backups"

show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  backup <description>   Take a MongoDB backup and save it as a .tar.gz archive in $BACKUP_DIR"
    echo "  restore <filepath>     Restore a MongoDB backup from the given .tar.gz archive"
    echo ""
    echo "Options:"
    echo "  --help, -h             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 backup before_big_change"
    echo "  $0 restore ./backups/20260311_120000_before_big_change.archive.tar.gz"
}

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

COMMAND=$1

case "$COMMAND" in
    backup)
        DESCRIPTION=$2
        if [ -z "$DESCRIPTION" ]; then
            echo "Error: Description is required for backup."
            echo "Example: $0 backup pre_deployment"
            exit 1
        fi

        mkdir -p "$BACKUP_DIR"
        
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        FILENAME="${TIMESTAMP}_${DESCRIPTION}.archive"
        TAR_FILENAME="${FILENAME}.tar.gz"
        
        echo "Starting backup of mongodb container..."
        echo "1. Creating mongodump inside container..."
        docker exec mongodb sh -c "mongodump --archive=/tmp/${FILENAME}"
        
        echo "2. Copying archive to host..."
        docker cp mongodb:/tmp/${FILENAME} ./${FILENAME}
        
        echo "3. Creating tar.gz archive..."
        tar -czf "${BACKUP_DIR}/${TAR_FILENAME}" "${FILENAME}"
        
        echo "4. Cleaning up temporary files..."
        rm ./${FILENAME}
        docker exec mongodb rm "/tmp/${FILENAME}"
        
        echo "Backup successfully created at: ${BACKUP_DIR}/${TAR_FILENAME}"
        ;;
        
    restore)
        BACKUP_FILE=$2
        if [ -z "$BACKUP_FILE" ]; then
            echo "Error: Path to backup file is required for restore."
            echo "Example: $0 restore ./backups/my_backup.archive.tar.gz"
            exit 1
        fi
        
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "Error: Backup file not found at $BACKUP_FILE"
            exit 1
        fi
        
        echo "Starting restore from ${BACKUP_FILE}..."
        
        # Determine the archive name inside the tar
        ARCHIVE_NAME=$(tar -tzf "$BACKUP_FILE" | head -1)
        
        if [ -z "$ARCHIVE_NAME" ]; then
            echo "Error: Failed to find an archive inside the tar file."
            exit 1
        fi
        
        echo "1. Extracting tar.gz archive..."
        tar -xzf "$BACKUP_FILE"
        
        echo "2. Copying archive to container..."
        docker cp ./${ARCHIVE_NAME} mongodb:/tmp/${ARCHIVE_NAME}
        
        echo "Warning: Starting mongorestore which will OVERWRITE data."
        echo "3. Running mongorestore inside container..."
        docker exec mongodb sh -c "mongorestore --archive=/tmp/${ARCHIVE_NAME} --drop"
        
        echo "4. Cleaning up temporary files..."
        rm ./${ARCHIVE_NAME}
        docker exec mongodb rm "/tmp/${ARCHIVE_NAME}"
        
        echo "Database successfully restored from ${BACKUP_FILE}"
        ;;
        
    *)
        echo "Error: Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
