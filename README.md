gcloud config set project ro-igpr-speech-to-text
NEW_BUCKET=tomis-ai-public
gsutil mb -l europe-west1 gs://$NEW_BUCKET

gsutil -m rsync -r gs://ro-igpr-speech-to-text-workspace gs://$NEW_BUCKET

gsutil ls gs://$NEW_BUCKET
gcloud storage buckets describe gs://$NEW_BUCKET --format="value(iamConfiguration.publicAccessPrevention)"

PROJECT=ro-igpr-speech-to-text
SA_NAME=tomis-tomisai-run
SA_EMAIL=${SA_NAME}@${PROJECT}.iam.gserviceaccount.com

gcloud iam service-accounts create $SA_NAME --display-name="Tomis AI Cloud Run SA"


gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:${SA_EMAIL}" --role="roles/run.admin"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:${SA_EMAIL}" --role="roles/storage.objectViewer"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:${SA_EMAIL}" --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:${SA_EMAIL}" --role="roles/aiplatform.user"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:${SA_EMAIL}" --role="roles/cloudbuild.builds.builder"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com speech.googleapis.com storage.googleapis.com aiplatform.googleapis.com


########################################################################
gcloud builds submit --tag gcr.io/ro-igpr-speech-to-text/tomis-ai:latest
gcloud run deploy tomis-ai \
  --image gcr.io/ro-igpr-speech-to-text/tomis-ai:latest \
  --region europe-west1 \
  --platform managed


