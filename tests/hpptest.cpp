#include <vulkan/vulkan.hpp>
int main()
{
    auto const instance_info = vk::InstanceCreateInfo();
    vk::Instance instance;
    vk::createInstance(&instance_info, nullptr, &instance);
}
