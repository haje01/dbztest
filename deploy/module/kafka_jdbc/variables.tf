variable "name" {}
variable "ubuntu_ami" {}
variable "kafka_instance_type" {
  default = "t3.medium"
}
variable "work_cidr" {}
variable "key_pair_name" {}
variable "private_key" {}
variable "consumer_sg_id" {}

variable "kafka_url" {}
variable "kafka_jdbc_connector" {}
variable "mysql_jdbc_driver" {}

variable "tags" {
    type = map(string)
}